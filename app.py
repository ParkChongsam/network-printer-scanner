import os
import json
import time
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

# 네트워크 스캐너 초기화
scanner = NetworkScanner()

# 등록된 장치 목록 저장
registered_devices = []

@app.route('/')
def index():
    """메인 페이지 렌더링"""
    return render_template('index.html')

@app.route('/api/scan', methods=['POST'])
def scan_device():
    """단일 IP 주소 스캔 실행"""
    try:
        # 요청에서 IP 주소 가져오기
        ip_address = request.json.get('ip_address')
        
        if not ip_address:
            return jsonify({
                'success': False,
                'message': 'IP 주소를 입력해주세요.'
            }), 400
        
        # 스캔 실행
        device_info = scanner.scan(ip_address)
        
        if device_info:
            # 이미 등록된 장치인지 확인
            existing_device = next((d for d in registered_devices if d['ip'] == ip_address), None)
            
            if existing_device:
                # 기존 장치 정보 업데이트
                for key, value in device_info.items():
                    existing_device[key] = value
                existing_device['last_update'] = time.strftime("%Y-%m-%d %H:%M:%S")
                
                return jsonify({
                    'success': True,
                    'message': f'장치 정보가 업데이트되었습니다: {device_info["name"]} ({ip_address})',
                    'device': existing_device,
                    'is_new': False
                })
            else:
                # 새 장치 등록
                device_info['last_update'] = time.strftime("%Y-%m-%d %H:%M:%S")
                registered_devices.append(device_info)
                
                return jsonify({
                    'success': True,
                    'message': f'새 장치가 등록되었습니다: {device_info["name"]} ({ip_address})',
                    'device': device_info,
                    'is_new': True
                })
        else:
            return jsonify({
                'success': False,
                'message': f'IP 주소 {ip_address}에서 프린터/복사기를 찾을 수 없습니다.'
            }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'스캔 중 오류 발생: {str(e)}'
        }), 500

@app.route('/api/devices', methods=['GET'])
def get_devices():
    """등록된 장치 목록 반환"""
    return jsonify({
        'devices': registered_devices,
        'device_count': len(registered_devices)
    })

@app.route('/api/device/<ip>', methods=['GET'])
def get_device_details(ip):
    """특정 장치의 상세 정보 반환"""
    try:
        # IP 주소로 장치 찾기
        device = next((d for d in registered_devices if d['ip'] == ip), None)
        
        if not device:
            return jsonify({
                'success': False,
                'message': f'IP {ip}에 해당하는 장치를 찾을 수 없습니다.'
            }), 404
            
        # 장치 상세 정보 가져오기
        details = scanner.get_device_details(ip)
        
        return jsonify({
            'success': True,
            'device': details,
            'last_update': time.strftime("%Y-%m-%d %H:%M:%S")
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'장치 정보 조회 중 오류 발생: {str(e)}'
        }), 500

@app.route('/api/device/<ip>', methods=['DELETE'])
def delete_device(ip):
    """등록된 장치 삭제"""
    try:
        # IP 주소로 장치 찾기
        device = next((d for d in registered_devices if d['ip'] == ip), None)
        
        if not device:
            return jsonify({
                'success': False,
                'message': f'IP {ip}에 해당하는 장치를 찾을 수 없습니다.'
            }), 404
        
        # 장치 삭제
        registered_devices.remove(device)
        
        return jsonify({
            'success': True,
            'message': f'장치가 삭제되었습니다: {device["name"]} ({ip})'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'장치 삭제 중 오류 발생: {str(e)}'
        }), 500

if __name__ == '__main__':
    app.run(host=HOST, port=PORT, debug=DEBUG) 