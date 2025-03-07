import os
import json
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
from scanner import NetworkScanner

# 환경 변수 로드
load_dotenv()

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

# 환경 변수에서 설정 가져오기
DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 't')
PORT = int(os.getenv('PORT', 5000))
HOST = os.getenv('HOST', '0.0.0.0')
NETWORK_RANGE = os.getenv('NETWORK_RANGE', '192.168.0.0/24')
SCAN_INTERVAL = int(os.getenv('SCAN_INTERVAL', 300))

# 네트워크 스캐너 초기화
scanner = NetworkScanner(NETWORK_RANGE)

# 마지막 스캔 결과 저장
last_scan_results = []

@app.route('/')
def index():
    """메인 페이지 렌더링"""
    return render_template('index.html')

@app.route('/api/scan', methods=['POST'])
def scan_network():
    """네트워크 스캔 실행"""
    try:
        # 요청에서 네트워크 범위 가져오기 (없으면 기본값 사용)
        network_range = request.json.get('network_range', NETWORK_RANGE)
        scanner.network_range = network_range
        
        # 스캔 실행
        global last_scan_results
        last_scan_results = scanner.scan()
        
        return jsonify({
            'success': True,
            'message': f'{len(last_scan_results)}개의 장치를 발견했습니다.',
            'devices': last_scan_results
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'스캔 중 오류 발생: {str(e)}'
        }), 500

@app.route('/api/devices', methods=['GET'])
def get_devices():
    """저장된 장치 목록 반환"""
    return jsonify(last_scan_results)

@app.route('/api/device/<ip>', methods=['GET'])
def get_device_details(ip):
    """특정 장치의 상세 정보 반환"""
    try:
        # IP 주소로 장치 찾기
        device = next((d for d in last_scan_results if d['ip'] == ip), None)
        
        if not device:
            return jsonify({
                'success': False,
                'message': f'IP {ip}에 해당하는 장치를 찾을 수 없습니다.'
            }), 404
            
        # 장치 상세 정보 가져오기
        details = scanner.get_device_details(ip)
        
        return jsonify({
            'success': True,
            'device': details
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'장치 정보 조회 중 오류 발생: {str(e)}'
        }), 500

if __name__ == '__main__':
    app.run(host=HOST, port=PORT, debug=DEBUG) 