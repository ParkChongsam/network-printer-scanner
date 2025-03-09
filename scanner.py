import os
import time
import socket
import requests
from datetime import datetime
import puresnmp

class NetworkScanner:
    """네트워크 스캐너 클래스"""
    
    def __init__(self):
        """
        네트워크 스캐너 초기화
        """
        self.snmp_community = os.getenv('SNMP_COMMUNITY', 'public')
        self.snmp_version = int(os.getenv('SNMP_VERSION', 2))
        
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
    
    def scan(self, ip_address):
        """
        단일 IP 주소 스캔 실행
        
        Args:
            ip_address (str): 스캔할 IP 주소
            
        Returns:
            dict: 발견된 프린터/복사기 장치 정보 (장치가 없으면 None)
        """
        print(f"IP 주소 {ip_address} 스캔 시작...")
        
        try:
            # IP 주소가 유효한지 확인
            socket.inet_aton(ip_address)
            
            # IP 주소가 프린터/복사기인지 확인
            if self._is_printer(ip_address):
                print(f"IP 주소 {ip_address}에서 프린터/복사기를 발견했습니다.")
                device_info = self._get_basic_device_info(ip_address)
                print(f"장치 정보: {device_info}")
                return device_info
            
            print(f"IP 주소 {ip_address}에서 프린터/복사기를 찾을 수 없습니다.")
            return None
        except socket.error:
            print(f"유효하지 않은 IP 주소 형식: {ip_address}")
            return None
        except Exception as e:
            print(f"IP 주소 {ip_address} 스캔 중 오류 발생: {str(e)}")
            return None
    
    def _is_printer(self, ip):
        """
        IP 주소가 프린터/복사기인지 확인
        
        Args:
            ip (str): 확인할 IP 주소
            
        Returns:
            bool: 프린터/복사기이면 True, 아니면 False
        """
        print(f"IP {ip} 확인 중...")
        
        # 1. 포트 확인
        open_ports = []
        for port in self.printer_ports:
            if self._check_port(ip, port):
                open_ports.append(port)
                print(f"IP {ip}의 포트 {port}가 열려 있습니다.")
        
        if not open_ports:
            print(f"IP {ip}에서 열린 프린터 관련 포트를 찾을 수 없습니다.")
            return False
        
        # 2. SNMP 확인
        system_desc = self._get_snmp_value(ip, self.oids['system_description'])
        if system_desc:
            print(f"IP {ip}의 SNMP 시스템 설명: {system_desc}")
            system_desc = system_desc.lower()
            
            # 제조사 이름이 시스템 설명에 포함되어 있는지 확인
            for manufacturer in self.printer_manufacturers:
                if manufacturer in system_desc:
                    print(f"IP {ip}는 {manufacturer} 제조사의 프린터/복사기입니다.")
                    return True
        else:
            print(f"IP {ip}에서 SNMP 정보를 가져올 수 없습니다.")
        
        # 3. HTTP 확인 (웹 인터페이스)
        if 80 in open_ports or 443 in open_ports:
            try:
                protocol = 'https' if 443 in open_ports else 'http'
                print(f"IP {ip}의 웹 인터페이스 확인 중 ({protocol})...")
                response = requests.get(f"{protocol}://{ip}", timeout=2, verify=False)
                page_content = response.text.lower()
                
                # 프린터 관련 키워드 확인
                printer_keywords = ['printer', 'copier', 'scanner', 'mfp', 'multifunction', '프린터', '복사기', '스캐너', '복합기']
                for keyword in printer_keywords:
                    if keyword in page_content:
                        print(f"IP {ip}의 웹 페이지에서 '{keyword}' 키워드를 발견했습니다.")
                        return True
                
                print(f"IP {ip}의 웹 페이지에서 프린터 관련 키워드를 찾을 수 없습니다.")
            except requests.exceptions.RequestException as e:
                print(f"HTTP 요청 실패 ({ip}): {str(e)}")
            except Exception as e:
                print(f"HTTP 확인 중 예외 발생 ({ip}): {str(e)}")
        
        # 4. 프린터 포트가 열려 있으면 프린터로 간주 (더 관대한 검사)
        if 9100 in open_ports or 515 in open_ports or 631 in open_ports:
            print(f"IP {ip}는 프린터 관련 포트({open_ports})가 열려 있어 프린터/복사기로 간주합니다.")
            return True
        
        print(f"IP {ip}는 프린터/복사기가 아닌 것으로 판단됩니다.")
        return False
    
    def _check_port(self, ip, port):
        """
        IP 주소의 특정 포트가 열려있는지 확인
        
        Args:
            ip (str): 확인할 IP 주소
            port (int): 확인할 포트 번호
            
        Returns:
            bool: 포트가 열려있으면 True, 아니면 False
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)  # 3초 타임아웃 (더 긴 시간으로 설정)
        result = False
        try:
            print(f"IP {ip}의 포트 {port} 연결 시도 중...")
            result = sock.connect_ex((ip, port)) == 0
            if result:
                print(f"IP {ip}의 포트 {port}가 열려 있습니다.")
            else:
                print(f"IP {ip}의 포트 {port}가 닫혀 있습니다.")
        except socket.error as e:
            print(f"IP {ip}의 포트 {port} 확인 중 소켓 오류: {str(e)}")
        except Exception as e:
            print(f"IP {ip}의 포트 {port} 확인 중 예외 발생: {str(e)}")
        finally:
            sock.close()
        return result
    
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
        
        # 토너 색상별 처리
        toner_colors = ['black', 'cyan', 'magenta', 'yellow']
        
        for color in toner_colors:
            level_oid = self.oids[f'{color}_toner_level']
            max_oid = self.oids[f'{color}_toner_max']
            
            level = self._get_snmp_value(ip, level_oid)
            max_value = self._get_snmp_value(ip, max_oid)
            
            if level and max_value:
                try:
                    level = int(level)
                    max_value = int(max_value)
                    percent = int((level / max_value) * 100) if max_value > 0 else 0
                    
                    toner_info[color] = {
                        'level': level,
                        'max': max_value,
                        'percent': percent
                    }
                except (ValueError, TypeError) as e:
                    print(f"{color} 토너 정보 변환 중 오류 ({ip}): {str(e)}")
        
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
            print(f"IP {ip}에서 SNMP OID {oid} 값 요청 중...")
            # puresnmp를 사용하여 SNMP 값 가져오기
            result = puresnmp.get(
                ip,
                self.snmp_community,
                oid,
                timeout=2,
                version=self.snmp_version
            )
            
            # 결과가 bytes 타입이면 디코딩
            if isinstance(result, bytes):
                try:
                    decoded = result.decode('utf-8')
                    print(f"SNMP 값 (UTF-8): {decoded}")
                    return decoded
                except UnicodeDecodeError:
                    hex_value = result.hex()
                    print(f"SNMP 값 (HEX): {hex_value}")
                    return hex_value
            
            print(f"SNMP 값: {result}")
            return str(result)
        except Exception as e:
            # 디버깅을 위해 예외 정보 출력
            print(f"SNMP 값 가져오기 실패 ({ip}, {oid}): {str(e)}")
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