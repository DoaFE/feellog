# /analyzer.py

import os
import argparse
from datetime import datetime
from pathlib import Path
import json
import requests
import time
import cv2
from core.analyzer.video_analyzer import BatchVideoAnalyzer
from core.analyzer.gemini_sentiment_aggregator import GeminiSentimentAggregator
from core.renderer.result_renderer import ResultRenderer
from core.utils.analysis_logger import AnalysisLogger


def record_from_webcam(duration_seconds: int, output_filename: str = "recorded_video.avi"):
    """웹캠에서 지정된 시간 동안 비디오를 녹화하고 파일로 저장합니다."""
    cap = cv2.VideoCapture(0)  # 0번 카메라(기본 웹캠) 열기
    if not cap.isOpened():
        print("오류: 웹캠을 열 수 없습니다.")
        return None

    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(output_filename, fourcc, 20.0, (640, 480))
    
    start_time = time.time()
    print(f"{duration_seconds}초 동안 녹화를 시작합니다...")
    
    while (time.time() - start_time) < duration_seconds:
        ret, frame = cap.read()
        if not ret:
            print("오류: 프레임을 읽을 수 없습니다.")
            break
        out.write(frame)
        cv2.imshow('Recording...', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):  # 'q'를 누르면 녹화 중지
            break
            
    print("녹화가 완료되었습니다.")
    cap.release()
    out.release()
    cv2.destroyAllWindows()
    return output_filename

if __name__ == "__main__":
    # Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--video_path', type=str, help='분석할 동영상 파일 경로를 입력하세요.')
    parser.add_argument('--record_from_cam', type=int, help='웹캠에서 녹화할 시간(초)을 지정합니다. 이 옵션 사용 시 --video_path는 무시됩니다.')
    parser.add_argument('--output_video_path', type=str, default="recorded_video.avi", help='녹화된 비디오 파일의 출력 경로입니다.')
    parser.add_argument('--voice_model', type=str, default="wav2vec2",
                        choices=["wav2vec2", "hubert-base", "wav2vec2_autumn"],
                        help='음성 감정 분석에 사용할 모델을 선택하세요.')
    parser.add_argument('--min_speech_segment_duration', type=float, default=5.0,
                        help='최소 발화 세그먼트 지속 시간 (초).')
    parser.add_argument('--record_id', type=str, required=True, help='분석 대상 레코드 ID')
    parser.add_argument('--user_id', type=str, required=True, help='분석 요청 사용자 ID')
    args = parser.parse_args()
    
    VIDEO_FILE_PATH = None
    if args.record_from_cam:
        VIDEO_FILE_PATH = record_from_webcam(args.record_from_cam)
        if VIDEO_FILE_PATH is None:
            exit(1) # 녹화 실패 시 종료
    elif args.video_path:
        VIDEO_FILE_PATH = args.video_path
    else:
        print("오류: --video_path 또는 --record_from_cam 옵션 중 하나는 반드시 필요합니다.")
        exit(1)

    current_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    detailed_log_filename = f"./logs/detailed_analysis_log_{current_timestamp}.json"
    analysis_logger = AnalysisLogger()
    analysis_logger.log_info(f"분석 시작: {datetime.now().isoformat()}", {"arguments": vars(args)})
    
    IMAGE_MODEL_WEIGHTS = "infrastructure/models/emonet_100_2_trained.pth"

    GEMINI_API_KEY = None
    try:
        with open(".ignore/API.json", "r") as f:
            api_info = json.load(f)
        api_key_gemini = api_info.get("API_GEMINI")
        if not api_key_gemini or not api_key_gemini.get('key'):
            raise ValueError("API_GEMINI 키가 API.json에 없거나 유효하지 않습니다.")
        GEMINI_API_KEY = api_key_gemini['key']
    except FileNotFoundError:
        analysis_logger.log_error("오류: .ignore/API.json 파일을 찾을 수 없습니다. Gemini API 키를 설정해주세요.")
        exit(1)
    except (json.JSONDecodeError, ValueError) as e:
        analysis_logger.log_error(f"오류: API.json 파일 처리 중 에러 발생: {e}")
        exit(1)

    batch_analyzer = BatchVideoAnalyzer(
        image_model_name="emonet",
        image_model_weights_path=IMAGE_MODEL_WEIGHTS,
        api_key=GEMINI_API_KEY,
        voice_model_name=args.voice_model,
        min_speech_segment_duration=args.min_speech_segment_duration,
        logger=analysis_logger
    )

    analysis_results_from_segments = batch_analyzer.analyze(VIDEO_FILE_PATH)
    analysis_logger.save_intermediate_result("batch_video_analysis_full_results", analysis_results_from_segments)

    gemini_aggregator = GeminiSentimentAggregator(api_key=GEMINI_API_KEY, logger=analysis_logger)
    final_aggregated_sentiment = gemini_aggregator.aggregate_sentiment(
        analysis_results_from_segments.get("segment_analyses", [])
    )
    analysis_logger.save_intermediate_result("final_aggregated_sentiment_result", final_aggregated_sentiment)

    # HTML 카드 렌더링
    html_template_path = "./templates/card_template_01.html"
    current_script_dir = Path(__file__).parent
    full_html_template_path = current_script_dir / html_template_path
    template_dir = str(full_html_template_path.parent)
    template_filename = full_html_template_path.name
    result_renderer = ResultRenderer(template_dir=template_dir, template_filename=template_filename)
    rendered_html_content = result_renderer.render(final_aggregated_sentiment)

    # 최종 결과를 백엔드 API로 전송
    api_url = 'http://localhost:5000/api/save_analysis_results'
    payload = {
        "record_id": args.record_id,
        "user_id": args.user_id,
        "analysis_data": analysis_results_from_segments,
        "report_data": {
            "card": final_aggregated_sentiment,
            "detail": analysis_results_from_segments, # 상세 분석 데이터
            "summary": { # 추후 Gemini를 통해 생성될 요약 데이터
                "overall_score": final_aggregated_sentiment.get("sentiment_score"),
                "dominant_emotion": final_aggregated_sentiment.get("dominant_overall_emotion")
            }
        }
    }
    
    try:
        response = requests.post(api_url, json=payload)
        response.raise_for_status()
        analysis_logger.log_info("분석 결과 백엔드 API 전송 성공.")
    except requests.exceptions.RequestException as e:
        analysis_logger.log_error(f"분석 결과 백엔드 API 전송 실패: {e}")
        
    # 분석 완료 후 임시 파일 정리
    if os.path.exists(VIDEO_FILE_PATH):
        os.remove(VIDEO_FILE_PATH)
    
    analysis_logger.save_to_file(detailed_log_filename)
    print(f"\n모든 상세 로그 및 중간 결과는 '{detailed_log_filename}'에 저장되었습니다.")
    analysis_logger.log_info("모든 분석 및 로깅 프로세스 완료.")
