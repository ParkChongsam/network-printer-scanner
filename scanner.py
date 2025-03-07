import os
import nmap
import time
import socket
import requests
from datetime import datetime
from pysnmp.hlapi import *

class NetworkScanner:
    """네트워크 스캐너 클래스"""
    
    def __init__(self, network_range='192.168.0.0/24'):
        """
        네트워크 스캐너 초기화
        
        Args:
            network_range (str): 스캔할 네트워크 범위 (CIDR 표기법)
        """
        self.network_range = network_range
        self.snmp_community = os.getenv('SNMP_COMMUNITY', 'public')
        self.snmp_version = int(os.getenv('SNMP_VERSION', 2))
        self.nm = nmap.PortScanner()
        
        # 프린터/복사기 관련 포트
        self.printer_ports = [
            9100,  # Raw Print / JetDirect
            515,   # LPD (Line Printer Daemon)
            631,   # IPP (Internet Printing Protocol)
            80,    # HTTP (웹 인터페이스)
            443    # HTTPS (보안 웹 인터페이스)
        ]
        
        # 프린터/복사기 제조사 목록
        self.printer_manufacturers = [
            'brother', 'canon', 'epson', 'hp', 'konica', 'kyocera', 
            'lexmark', 'minolta', 'oki', 'ricoh', 'samsung', 'sharp', 
            'xerox', 'zebra'
        ]
        
        # SNMP OID 정의
        self.oids = {
            'system_description': '1.3.6.1.2.1.1.1.0',
            'system_name': '1.3.6.1.2.1.1.5.0',
            'system_location': '1.3.6.1.2.1.1.6.0',
            'system_contact': '1.3.6.1.2.1.1.4.0',
            'system_uptime': '1.3.6.1.2.1.1.3.0',
            
            # 프린터 MIB
            'printer_status': '1.3.6.1.2.1.25.3.5.1.1.1',
            'printer_name': '1.3.6.1.2.1.25.3.2.1.3.1',
            'printer_model': '1.3.6.1.2.1.25.3.2.1.3.1',
            'printer_serial': '1.3.6.1.2.1.43.5.1.1.17.1',
            
            # 토너 레벨
            'black_toner_level': '1.3.6.1.2.1.43.11.1.1.9.1.1',
            'cyan_toner_level': '1.3.6.1.2.1.43.11.1.1.9.1.2',
            'magenta_toner_level': '1.3.6.1.2.1.43.11.1.1.9.1.3',
            'yellow_toner_level': '1.3.6.1.2.1.43.11.1.1.9.1.4',
            
            # 토너 최대 용량
            'black_toner_max': '1.3.6.1.2.1.43.11.1.1.8.1.1',
            'cyan_toner_max': '1.3.6.1.2.1.43.11.1.1.8.1.2',
            'magenta_toner_max': '1.3.6.1.2.1.43.11.1.1.8.1.3',
            'yellow_toner_max': '1.3.6.1.2.1.43.11.1.1.8.1.4',
            
            # 페이지 카운터
            'page_counter': '1.3.6.1.2.1.43.10.2.1.4.1.1'
        }
    
    def scan(self):
        """
        네트워크 스캔 실행
        
        Returns:
            list: 발견된 프린터/복사기 장치 목록
        """
        print(f"네트워크 범위 {self.network_range} 스캔 중...")
        
        # 프린터 관련 포트 스캔
        port_list = ','.join(map(str, self.printer_ports))
        self.nm.scan(hosts=self.network_range, arguments=f'-p {port_list} --open')
        
        devices = []
        
        # 스캔 결과 처리
        for host in self.nm.all_hosts():
            # 장치가 프린터/복사기인지 확인
            if self._is_printer(host):
                device_info = self._get_basic_device_info(host)
                devices.append(device_info)
        
        print(f"{len(devices)}개의 프린터/복사기 장치를 발견했습니다.")
        return devices
    
    def _is_printer(self, ip):
        """
        IP 주소가 프린터/복사기인지 확인
        
        Args:
            ip (str): 확인할 IP 주소
            
        Returns:
            bool: 프린터/복사기이면 True, 아니면 False
        """
        # 1. 포트 확인
        for port in self.printer_ports:
            if port in self.nm[ip].get('tcp', {}):
                # 2. SNMP 확인
                system_desc = self._get_snmp_value(ip, self.oids['system_description'])
                if system_desc:
                    system_desc = system_desc.lower()
                    # 제조사 이름이 시스템 설명에 포함되어 있는지 확인
                    for manufacturer in self.printer_manufacturers:
                        if manufacturer in system_desc:
                            return True
                
                # 3. HTTP 확인 (웹 인터페이스)
                if 80 in self.nm[ip].get('tcp', {}) or 443 in self.nm[ip].get('tcp', {}):
                    try:
                        protocol = 'https' if 443 in self.nm[ip].get('tcp', {}) else 'http'
                        response = requests.get(f"{protocol}://{ip}", timeout=2)
                        page_content = response.text.lower()
                        
                        # 프린터 관련 키워드 확인
                        printer_keywords = ['printer', 'copier', 'scanner', 'mfp', 'multifunction']
                        for keyword in printer_keywords:
                            if keyword in page_content:
                                return True
                    except:
                        pass
        
        return False
    
    def _get_basic_device_info(self, ip):
        """
        장치의 기본 정보 가져오기
        
        Args:
            ip (str): 장치 IP 주소
            
        Returns:
            dict: 장치 기본 정보
        """
        # 현재 시간
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # SNMP로 정보 가져오기
        system_name = self._get_snmp_value(ip, self.oids['system_name']) or '알 수 없음'
        model = self._get_snmp_value(ip, self.oids['printer_model']) or '알 수 없음'
        serial = self._get_snmp_value(ip, self.oids['printer_serial']) or '알 수 없음'
        
        # 토너 정보 가져오기
        toner_info = self._get_toner_info(ip)
        
        # 페이지 카운터
        page_count = self._get_snmp_value(ip, self.oids['page_counter'])
        try:
            page_count = int(page_count)
        except:
            page_count = 0
        
        # 상태 확인
        status = "온라인"  # 기본값
        
        return {
            'ip': ip,
            'status': status,
            'name': system_name,
            'model': model,
            'serial': serial,
            'last_update': current_time,
            'toner': toner_info,
            'page_count': page_count
        }
    
    def get_device_details(self, ip):
        """
        장치의 상세 정보 가져오기
        
        Args:
            ip (str): 장치 IP 주소
            
        Returns:
            dict: 장치 상세 정보
        """
        # 기본 정보 가져오기
        device_info = self._get_basic_device_info(ip)
        
        # 추가 정보
        device_info['location'] = self._get_snmp_value(ip, self.oids['system_location']) or '알 수 없음'
        device_info['contact'] = self._get_snmp_value(ip, self.oids['system_contact']) or '알 수 없음'
        
        # 업타임
        uptime = self._get_snmp_value(ip, self.oids['system_uptime'])
        try:
            uptime = int(uptime) / 100  # 초 단위로 변환
            uptime_str = self._format_uptime(uptime)
            device_info['uptime'] = uptime_str
        except:
            device_info['uptime'] = '알 수 없음'
        
        return device_info
    
    def _get_toner_info(self, ip):
        """
        토너 정보 가져오기
        
        Args:
            ip (str): 장치 IP 주소
            
        Returns:
            dict: 토너 정보
        """
        toner_info = {
            'black': {'level': 0, 'max': 100, 'percent': 0},
            'cyan': {'level': 0, 'max': 100, 'percent': 0},
            'magenta': {'level': 0, 'max': 100, 'percent': 0},
            'yellow': {'level': 0, 'max': 100, 'percent': 0}
        }
        
        # 블랙 토너
        black_level = self._get_snmp_value(ip, self.oids['black_toner_level'])
        black_max = self._get_snmp_value(ip, self.oids['black_toner_max'])
        
        if black_level and black_max:
            try:
                black_level = int(black_level)
                black_max = int(black_max)
                black_percent = int((black_level / black_max) * 100) if black_max > 0 else 0
                
                toner_info['black'] = {
                    'level': black_level,
                    'max': black_max,
                    'percent': black_percent
                }
            except:
                pass
        
        # 컬러 토너 (시안)
        cyan_level = self._get_snmp_value(ip, self.oids['cyan_toner_level'])
        cyan_max = self._get_snmp_value(ip, self.oids['cyan_toner_max'])
        
        if cyan_level and cyan_max:
            try:
                cyan_level = int(cyan_level)
                cyan_max = int(cyan_max)
                cyan_percent = int((cyan_level / cyan_max) * 100) if cyan_max > 0 else 0
                
                toner_info['cyan'] = {
                    'level': cyan_level,
                    'max': cyan_max,
                    'percent': cyan_percent
                }
            except:
                pass
        
        # 컬러 토너 (마젠타)
        magenta_level = self._get_snmp_value(ip, self.oids['magenta_toner_level'])
        magenta_max = self._get_snmp_value(ip, self.oids['magenta_toner_max'])
        
        if magenta_level and magenta_max:
            try:
                magenta_level = int(magenta_level)
                magenta_max = int(magenta_max)
                magenta_percent = int((magenta_level / magenta_max) * 100) if magenta_max > 0 else 0
                
                toner_info['magenta'] = {
                    'level': magenta_level,
                    'max': magenta_max,
                    'percent': magenta_percent
                }
            except:
                pass
        
        # 컬러 토너 (옐로우)
        yellow_level = self._get_snmp_value(ip, self.oids['yellow_toner_level'])
        yellow_max = self._get_snmp_value(ip, self.oids['yellow_toner_max'])
        
        if yellow_level and yellow_max:
            try:
                yellow_level = int(yellow_level)
                yellow_max = int(yellow_max)
                yellow_percent = int((yellow_level / yellow_max) * 100) if yellow_max > 0 else 0
                
                toner_info['yellow'] = {
                    'level': yellow_level,
                    'max': yellow_max,
                    'percent': yellow_percent
                }
            except:
                pass
        
        return toner_info
    
    def _get_snmp_value(self, ip, oid):
        """
        SNMP 값 가져오기
        
        Args:
            ip (str): 장치 IP 주소
            oid (str): SNMP OID
            
        Returns:
            str: SNMP 값 (실패 시 None)
        """
        try:
            error_indication, error_status, error_index, var_binds = next(
                getCmd(
                    SnmpEngine(),
                    CommunityData(self.snmp_community, mpModel=self.snmp_version-1),
                    UdpTransportTarget((ip, 161), timeout=2, retries=1),
                    ContextData(),
                    ObjectType(ObjectIdentity(oid))
                )
            )
            
            if error_indication or error_status:
                return None
            
            return str(var_binds[0][1])
        except:
            return None
    
    def _format_uptime(self, seconds):
        """
        업타임을 읽기 쉬운 형식으로 변환
        
        Args:
            seconds (float): 초 단위 업타임
            
        Returns:
            str: 형식화된 업타임 문자열
        """
        days = int(seconds // 86400)
        seconds %= 86400
        hours = int(seconds // 3600)
        seconds %= 3600
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        
        if days > 0:
            return f"{days}일 {hours}시간 {minutes}분"
        elif hours > 0:
            return f"{hours}시간 {minutes}분"
        elif minutes > 0:
            return f"{minutes}분 {seconds}초"
        else:
            return f"{seconds}초" 