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
        
        # 공통 SNMP OID 정의 (OID.md 참조)
        self.common_oids = {
            'sys_object_id': '1.3.6.1.2.1.1.2.0',      # 제조사 구분
            'sys_description': '1.3.6.1.2.1.1.1.0',    # 장치 설명, 모델명 포함
            'sys_name': '1.3.6.1.2.1.1.5.0',           # 호스트명
            'sys_location': '1.3.6.1.2.1.1.6.0',       # 설치 위치
            'sys_contact': '1.3.6.1.2.1.1.4.0',        # 담당자 정보
            'sys_uptime': '1.3.6.1.2.1.1.3.0',         # 가동 시간
            'page_counter': '1.3.6.1.2.1.43.10.2.1.4.1.1'  # 총 인쇄 매수 (공통)
        }
        
        # 제조사별 OID 정의 (OID.md 참조)
        self.manufacturer_oids = {
            'hp': {
                'product_name': '1.3.6.1.2.1.1.1.0',           # 제품명
                'toner_black': '1.3.6.1.2.1.43.11.1.1.9.1.1',  # 토너 잔량 (Black)
                'toner_cyan': '1.3.6.1.2.1.43.11.1.1.9.1.2',   # 토너 잔량 (Cyan)
                'toner_magenta': '1.3.6.1.2.1.43.11.1.1.9.1.3', # 토너 잔량 (Magenta)
                'toner_yellow': '1.3.6.1.2.1.43.11.1.1.9.1.4', # 토너 잔량 (Yellow)
                'toner_black_max': '1.3.6.1.2.1.43.11.1.1.8.1.1', # 토너 최대 용량 (Black)
                'toner_cyan_max': '1.3.6.1.2.1.43.11.1.1.8.1.2', # 토너 최대 용량 (Cyan)
                'toner_magenta_max': '1.3.6.1.2.1.43.11.1.1.8.1.3', # 토너 최대 용량 (Magenta)
                'toner_yellow_max': '1.3.6.1.2.1.43.11.1.1.8.1.4', # 토너 최대 용량 (Yellow)
                'page_count': '1.3.6.1.2.1.43.10.2.1.4.1.1',    # 총 인쇄 매수
                'object_id_prefix': '1.3.6.1.4.1.11'            # HP 제조사 OID 접두사
            },
            'canon': {
                'product_name': '1.3.6.1.2.1.1.1.0',           # 제품명
                'toner_black': '1.3.6.1.4.1.160.1.12.3.1.2.1.1', # 토너 잔량 (Black)
                'toner_cyan': '1.3.6.1.4.1.160.1.12.3.1.2.1.2', # 토너 잔량 (Cyan)
                'toner_magenta': '1.3.6.1.4.1.160.1.12.3.1.2.1.3', # 토너 잔량 (Magenta)
                'toner_yellow': '1.3.6.1.4.1.160.1.12.3.1.2.1.4', # 토너 잔량 (Yellow)
                'page_count': '1.3.6.1.2.1.43.10.2.1.4.1.1',    # 총 인쇄 매수
                'object_id_prefix': '1.3.6.1.4.1.160'           # Canon 제조사 OID 접두사
            },
            'ricoh': {
                'product_name': '1.3.6.1.2.1.1.1.0',           # 제품명
                'toner_black': '1.3.6.1.4.1.367.3.2.1.1.4',    # 토너 잔량 (Black)
                'toner_cyan': '1.3.6.1.4.1.367.3.2.1.1.5',     # 토너 잔량 (Cyan)
                'toner_magenta': '1.3.6.1.4.1.367.3.2.1.1.6',  # 토너 잔량 (Magenta)
                'toner_yellow': '1.3.6.1.4.1.367.3.2.1.1.7',   # 토너 잔량 (Yellow)
                'page_count': '1.3.6.1.2.1.43.10.2.1.4.1.1',   # 총 인쇄 매수
                'object_id_prefix': '1.3.6.1.4.1.367'          # Ricoh 제조사 OID 접두사
            },
            'xerox': {
                'product_name': '1.3.6.1.2.1.1.1.0',           # 제품명
                'toner_black': '1.3.6.1.4.1.253.8.53.13.2',    # 토너 잔량 (Black)
                'toner_cyan': '1.3.6.1.4.1.253.8.53.13.3',     # 토너 잔량 (Cyan)
                'toner_magenta': '1.3.6.1.4.1.253.8.53.13.4',  # 토너 잔량 (Magenta)
                'toner_yellow': '1.3.6.1.4.1.253.8.53.13.5',   # 토너 잔량 (Yellow)
                'page_count': '1.3.6.1.2.1.43.10.2.1.4.1.1',   # 총 인쇄 매수
                'object_id_prefix': '1.3.6.1.4.1.253'          # Xerox 제조사 OID 접두사
            },
            'konica': {
                'product_name': '1.3.6.1.2.1.1.1.0',           # 제품명
                'toner_black': '1.3.6.1.4.1.2385.3.1.1.4',     # 토너 잔량 (Black)
                'toner_cyan': '1.3.6.1.4.1.2385.3.1.1.5',      # 토너 잔량 (Cyan)
                'toner_magenta': '1.3.6.1.4.1.2385.3.1.1.6',   # 토너 잔량 (Magenta)
                'toner_yellow': '1.3.6.1.4.1.2385.3.1.1.7',    # 토너 잔량 (Yellow)
                'page_count': '1.3.6.1.2.1.43.10.2.1.4.1.1',   # 총 인쇄 매수
                'object_id_prefix': '1.3.6.1.4.1.2385'         # Konica Minolta 제조사 OID 접두사
            },
            'default': {
                'product_name': '1.3.6.1.2.1.1.1.0',           # 제품명
                'toner_black': '1.3.6.1.2.1.43.11.1.1.9.1.1',  # 토너 잔량 (Black)
                'toner_cyan': '1.3.6.1.2.1.43.11.1.1.9.1.2',   # 토너 잔량 (Cyan)
                'toner_magenta': '1.3.6.1.2.1.43.11.1.1.9.1.3', # 토너 잔량 (Magenta)
                'toner_yellow': '1.3.6.1.2.1.43.11.1.1.9.1.4', # 토너 잔량 (Yellow)
                'toner_black_max': '1.3.6.1.2.1.43.11.1.1.8.1.1', # 토너 최대 용량 (Black)
                'toner_cyan_max': '1.3.6.1.2.1.43.11.1.1.8.1.2', # 토너 최대 용량 (Cyan)
                'toner_magenta_max': '1.3.6.1.2.1.43.11.1.1.8.1.3', # 토너 최대 용량 (Magenta)
                'toner_yellow_max': '1.3.6.1.2.1.43.11.1.1.8.1.4', # 토너 최대 용량 (Yellow)
                'page_count': '1.3.6.1.2.1.43.10.2.1.4.1.1'    # 총 인쇄 매수
            }
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
        system_desc = self._get_snmp_value(ip, self.common_oids['sys_description'])
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
        
        # 제조사 식별
        manufacturer = self._identify_manufacturer(ip)
        print(f"식별된 제조사: {manufacturer}")
        
        # 제조사별 OID 선택
        oids = self.manufacturer_oids.get(manufacturer, self.manufacturer_oids['default'])
        
        # 제품명 가져오기 (OID.md 참조)
        product_name = self._get_snmp_value(ip, oids['product_name']) or '알 수 없음'
        print(f"제품명: {product_name}")
        
        # 시스템 정보 가져오기
        system_name = self._get_snmp_value(ip, self.common_oids['sys_name']) or '알 수 없음'
        system_location = self._get_snmp_value(ip, self.common_oids['sys_location']) or '알 수 없음'
        
        # 시리얼 번호 (제조사별로 다를 수 있음)
        serial = self._get_serial_number(ip, manufacturer) or '알 수 없음'
        print(f"시리얼 번호: {serial}")
        
        # 토너 정보 가져오기
        toner_info = self._get_toner_info(ip, manufacturer, oids)
        
        # 페이지 카운터 (총 인쇄 매수)
        page_count = self._get_snmp_value(ip, oids['page_count'])
        try:
            page_count = int(page_count)
            print(f"총 인쇄 매수: {page_count}")
        except:
            page_count = 0
            print("총 인쇄 매수를 가져올 수 없습니다.")
        
        # 상태 확인
        status = "온라인"  # 기본값
        
        # 장치 정보 구성
        device_info = {
            'ip': ip,
            'status': status,
            'name': system_name,
            'location': system_location,
            'model': product_name,  # 제품명을 모델로 사용
            'manufacturer': manufacturer,
            'serial': serial,
            'last_update': current_time,
            'toner': toner_info,
            'page_count': page_count
        }
        
        print(f"장치 정보 수집 완료: {device_info['model']} ({ip})")
        return device_info
    
    def _identify_manufacturer(self, ip):
        """
        장치의 제조사 식별
        
        Args:
            ip (str): 장치 IP 주소
            
        Returns:
            str: 제조사 이름 (식별 실패 시 'default')
        """
        print(f"제조사 식별 중 ({ip})...")
        
        # 1. 시스템 객체 ID로 제조사 식별 (OID.md 참조)
        sys_object_id = self._get_snmp_value(ip, self.common_oids['sys_object_id'])
        if sys_object_id:
            print(f"시스템 객체 ID: {sys_object_id}")
            
            # 제조사별 OID 접두사 확인
            manufacturer_prefixes = {
                'hp': '1.3.6.1.4.1.11',       # HP
                'canon': '1.3.6.1.4.1.160',   # Canon
                'ricoh': '1.3.6.1.4.1.367',   # Ricoh
                'xerox': '1.3.6.1.4.1.253',   # Xerox
                'konica': '1.3.6.1.4.1.2385', # Konica Minolta
                'brother': '1.3.6.1.4.1.2435', # Brother
                'lexmark': '1.3.6.1.4.1.641', # Lexmark
                'samsung': '1.3.6.1.4.1.236', # Samsung
                'epson': '1.3.6.1.4.1.1248',  # Epson
                'kyocera': '1.3.6.1.4.1.1347' # Kyocera
            }
            
            for mfr, prefix in manufacturer_prefixes.items():
                if sys_object_id.startswith(prefix):
                    print(f"제조사 식별 완료: {mfr} (객체 ID 기준)")
                    return mfr
        
        # 2. 시스템 설명으로 제조사 식별
        sys_desc = self._get_snmp_value(ip, self.common_oids['sys_description'])
        if sys_desc:
            sys_desc = sys_desc.lower()
            print(f"시스템 설명: {sys_desc}")
            
            for manufacturer in self.printer_manufacturers:
                if manufacturer in sys_desc:
                    print(f"제조사 식별 완료: {manufacturer} (설명 기준)")
                    return manufacturer
        
        print("제조사를 식별할 수 없습니다. 기본 OID를 사용합니다.")
        return 'default'
    
    def _extract_model_from_description(self, description):
        """
        시스템 설명에서 모델명 추출
        
        Args:
            description (str): 시스템 설명
            
        Returns:
            str: 추출된 모델명
        """
        if not description or description == '알 수 없음':
            return '알 수 없음'
        
        # 일반적으로 시스템 설명에는 모델명이 포함되어 있음
        # 여기서는 간단히 전체 설명을 반환
        return description
    
    def _get_serial_number(self, ip, manufacturer):
        """
        장치의 시리얼 번호 가져오기
        
        Args:
            ip (str): 장치 IP 주소
            manufacturer (str): 제조사 이름
            
        Returns:
            str: 시리얼 번호 (실패 시 None)
        """
        # 일반적인 시리얼 번호 OID
        serial_oid = '1.3.6.1.2.1.43.5.1.1.17.1'
        
        # 제조사별 시리얼 번호 OID (필요시 추가)
        manufacturer_serial_oids = {
            'hp': '1.3.6.1.2.1.43.5.1.1.17.1',
            'canon': '1.3.6.1.2.1.43.5.1.1.17.1',
            'ricoh': '1.3.6.1.4.1.367.3.2.1.2.1.4.0',
            'xerox': '1.3.6.1.2.1.43.5.1.1.17.1',
            'konica': '1.3.6.1.2.1.43.5.1.1.17.1'
        }
        
        # 제조사별 OID 사용
        if manufacturer in manufacturer_serial_oids:
            serial = self._get_snmp_value(ip, manufacturer_serial_oids[manufacturer])
            if serial:
                return serial
        
        # 기본 OID 사용
        return self._get_snmp_value(ip, serial_oid)
    
    def _get_toner_info(self, ip, manufacturer, oids):
        """
        토너 정보 가져오기
        
        Args:
            ip (str): 장치 IP 주소
            manufacturer (str): 제조사 이름
            oids (dict): 사용할 OID 딕셔너리
            
        Returns:
            dict: 토너 정보
        """
        print(f"토너 정보 수집 중 ({manufacturer})...")
        
        toner_info = {
            'black': {'level': 0, 'max': 100, 'percent': 0},
            'cyan': {'level': 0, 'max': 100, 'percent': 0},
            'magenta': {'level': 0, 'max': 100, 'percent': 0},
            'yellow': {'level': 0, 'max': 100, 'percent': 0}
        }
        
        # 토너 색상별 처리
        toner_colors = ['black', 'cyan', 'magenta', 'yellow']
        
        for color in toner_colors:
            # 토너 레벨 OID
            level_oid = oids.get(f'toner_{color}')
            if not level_oid:
                print(f"{color} 토너 OID를 찾을 수 없습니다.")
                continue
                
            level = self._get_snmp_value(ip, level_oid)
            if level:
                print(f"{color} 토너 레벨: {level}")
            
            # 최대값 OID (일부 제조사는 직접 퍼센트를 반환)
            max_oid = oids.get(f'toner_{color}_max')
            max_value = 100  # 기본값
            
            if max_oid:
                max_value_str = self._get_snmp_value(ip, max_oid)
                if max_value_str:
                    try:
                        max_value = int(max_value_str)
                        print(f"{color} 토너 최대값: {max_value}")
                    except:
                        max_value = 100
            
            if level:
                try:
                    level_value = int(level)
                    
                    # 제조사별 특별 처리 (OID.md 참조)
                    if manufacturer in ['ricoh', 'xerox', 'konica']:
                        # 이미 퍼센트로 반환하는 제조사
                        percent = level_value
                    else:
                        # 레벨과 최대값으로 퍼센트 계산
                        percent = int((level_value / max_value) * 100) if max_value > 0 else 0
                    
                    print(f"{color} 토너 잔량: {percent}%")
                    
                    toner_info[color] = {
                        'level': level_value,
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
        device_info['uptime'] = '알 수 없음'
        
        # 업타임
        uptime = self._get_snmp_value(ip, self.common_oids['sys_uptime'])
        if uptime:
            try:
                uptime = int(uptime) / 100  # 초 단위로 변환
                uptime_str = self._format_uptime(uptime)
                device_info['uptime'] = uptime_str
            except:
                pass
        
        return device_info 