// 전역 변수
let devices = [];
let settings = {
    snmpCommunity: 'public',
    snmpVersion: 2
};

// DOM이 로드된 후 실행
document.addEventListener('DOMContentLoaded', function() {
    // 설정 로드
    loadSettings();
    
    // 이벤트 리스너 등록
    document.getElementById('scan-btn').addEventListener('click', scanDevice);
    document.getElementById('refresh-btn').addEventListener('click', refreshDevices);
    document.getElementById('save-settings').addEventListener('click', saveSettings);
    document.getElementById('export-btn').addEventListener('click', exportToExcel);
    document.getElementById('search-input').addEventListener('input', filterDevices);
    
    // IP 주소 입력 필드에서 Enter 키 이벤트 처리
    document.getElementById('ip-address-input').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            scanDevice();
        }
    });
    
    // 초기 장치 목록 로드
    loadDevices();
});

// 설정 로드
function loadSettings() {
    const savedSettings = localStorage.getItem('printerScannerSettings');
    if (savedSettings) {
        settings = JSON.parse(savedSettings);
    }
    
    // 설정 폼에 값 설정
    document.getElementById('snmp-community').value = settings.snmpCommunity;
    document.getElementById('snmp-version').value = settings.snmpVersion;
}

// 설정 저장
function saveSettings() {
    // 폼에서 값 가져오기
    settings.snmpCommunity = document.getElementById('snmp-community').value;
    settings.snmpVersion = parseInt(document.getElementById('snmp-version').value);
    
    // 로컬 스토리지에 저장
    localStorage.setItem('printerScannerSettings', JSON.stringify(settings));
    
    // 모달 닫기
    const modal = bootstrap.Modal.getInstance(document.getElementById('settingsModal'));
    modal.hide();
    
    // 성공 메시지 표시
    showSuccess('설정이 저장되었습니다.');
}

// 장치 목록 로드
function loadDevices() {
    fetch('/api/devices')
        .then(response => response.json())
        .then(data => {
            devices = data.devices;
            displayDevices(devices);
        })
        .catch(error => {
            console.error('장치 목록 로드 오류:', error);
            showError('장치 목록을 불러오는 중 오류가 발생했습니다.');
        });
}

// 장치 목록 새로고침
function refreshDevices() {
    loadDevices();
    showInfo('장치 목록을 새로고침했습니다.');
}

// 단일 장치 스캔
function scanDevice() {
    // IP 주소 가져오기
    const ipAddress = document.getElementById('ip-address-input').value.trim();
    
    if (!ipAddress) {
        showError('IP 주소를 입력해주세요.');
        return;
    }
    
    // IP 주소 유효성 검사
    if (!isValidIpAddress(ipAddress)) {
        showError('유효한 IP 주소를 입력해주세요. (예: 192.168.0.100)');
        return;
    }
    
    // 스캔 버튼 비활성화
    const scanBtn = document.getElementById('scan-btn');
    scanBtn.disabled = true;
    scanBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 스캔 중...';
    
    // API 호출
    fetch('/api/scan', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            ip_address: ipAddress
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // 장치 목록 새로고침
            loadDevices();
            
            // 성공 메시지 표시
            showSuccess(data.message);
            
            // IP 주소 입력 필드 초기화
            document.getElementById('ip-address-input').value = '';
        } else {
            // 오류 메시지 표시
            showError(data.message);
        }
    })
    .catch(error => {
        showError('스캔 중 오류가 발생했습니다: ' + error.message);
    })
    .finally(() => {
        // 스캔 버튼 활성화
        scanBtn.disabled = false;
        scanBtn.innerHTML = '<i class="bi bi-search me-1"></i>스캔';
    });
}

// IP 주소 유효성 검사
function isValidIpAddress(ipAddress) {
    const ipPattern = /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/;
    if (!ipPattern.test(ipAddress)) {
        return false;
    }
    
    const parts = ipAddress.split('.');
    for (let i = 0; i < 4; i++) {
        const part = parseInt(parts[i]);
        if (part < 0 || part > 255) {
            return false;
        }
    }
    
    return true;
}

// 장치 목록 표시
function displayDevices(devicesList) {
    const tbody = document.getElementById('devices-list');
    
    // 데이터가 없으면 비어있는 메시지 표시
    if (!devicesList || devicesList.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center py-5">
                    <p class="mb-0">등록된 복사기가 없습니다. IP 주소를 입력하고 스캔 버튼을 클릭하세요.</p>
                </td>
            </tr>
        `;
        return;
    }
    
    // 장치 목록 생성
    let html = '';
    devicesList.forEach((device, index) => {
        // 상태 아이콘 결정
        let statusClass = 'status-online';
        let statusText = '온라인';
        
        if (device.status && device.status.toLowerCase() === 'offline') {
            statusClass = 'status-offline';
            statusText = '오프라인';
        } else if (device.status && device.status.toLowerCase() === 'warning') {
            statusClass = 'status-warning';
            statusText = '경고';
        }
        
        // 토너 상태 HTML 생성
        const tonerHtml = generateTonerHtml(device.toner);
        
        // 행 HTML 생성
        html += `
            <tr class="clickable-row" data-ip="${device.ip}">
                <td>
                    <span class="status-indicator ${statusClass}"></span>
                    ${statusText}
                </td>
                <td>${index + 1}</td>
                <td>${device.name || '알 수 없음'}</td>
                <td>${device.model || '알 수 없음'}</td>
                <td>${device.serial || '알 수 없음'}</td>
                <td>${device.ip}</td>
                <td>${tonerHtml}</td>
                <td>
                    <button class="btn btn-sm btn-outline-primary me-1 view-device" data-ip="${device.ip}" title="상세 정보">
                        <i class="bi bi-info-circle"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-danger delete-device" data-ip="${device.ip}" title="삭제">
                        <i class="bi bi-trash"></i>
                    </button>
                </td>
            </tr>
        `;
    });
    
    tbody.innerHTML = html;
    
    // 행 클릭 이벤트 등록
    document.querySelectorAll('.clickable-row').forEach(row => {
        row.addEventListener('click', function(e) {
            // 버튼 클릭은 무시
            if (e.target.closest('button')) {
                return;
            }
            
            const ip = this.getAttribute('data-ip');
            showDeviceDetails(ip);
        });
    });
    
    // 상세 정보 버튼 이벤트 등록
    document.querySelectorAll('.view-device').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
            const ip = this.getAttribute('data-ip');
            showDeviceDetails(ip);
        });
    });
    
    // 삭제 버튼 이벤트 등록
    document.querySelectorAll('.delete-device').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
            const ip = this.getAttribute('data-ip');
            const device = devices.find(d => d.ip === ip);
            
            if (confirm(`정말로 "${device.name || device.ip}" 장치를 삭제하시겠습니까?`)) {
                deleteDevice(ip);
            }
        });
    });
}

// 장치 삭제
function deleteDevice(ip) {
    fetch(`/api/device/${ip}`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // 장치 목록 새로고침
            loadDevices();
            
            // 성공 메시지 표시
            showSuccess(data.message);
        } else {
            // 오류 메시지 표시
            showError(data.message);
        }
    })
    .catch(error => {
        showError('장치 삭제 중 오류가 발생했습니다: ' + error.message);
    });
}

// 토너 상태 HTML 생성
function generateTonerHtml(toner) {
    let html = '';
    
    // 블랙 토너
    const blackPercent = toner.black.percent;
    let blackClass = 'toner-black';
    if (blackPercent <= 10) {
        blackClass += ' toner-danger';
    } else if (blackPercent <= 20) {
        blackClass += ' toner-warning';
    }
    
    html += `
        <div class="toner-bar">
            <div class="toner-level ${blackClass}" style="width: ${blackPercent}%">
                ${blackPercent}%
            </div>
        </div>
    `;
    
    // 컬러 토너가 있는 경우
    if (toner.cyan.percent > 0 || toner.magenta.percent > 0 || toner.yellow.percent > 0) {
        // 시안 토너
        const cyanPercent = toner.cyan.percent;
        let cyanClass = 'toner-cyan';
        if (cyanPercent <= 10) {
            cyanClass += ' toner-danger';
        } else if (cyanPercent <= 20) {
            cyanClass += ' toner-warning';
        }
        
        // 마젠타 토너
        const magentaPercent = toner.magenta.percent;
        let magentaClass = 'toner-magenta';
        if (magentaPercent <= 10) {
            magentaClass += ' toner-danger';
        } else if (magentaPercent <= 20) {
            magentaClass += ' toner-warning';
        }
        
        // 옐로우 토너
        const yellowPercent = toner.yellow.percent;
        let yellowClass = 'toner-yellow';
        if (yellowPercent <= 10) {
            yellowClass += ' toner-danger';
        } else if (yellowPercent <= 20) {
            yellowClass += ' toner-warning';
        }
        
        html += `
            <div class="toner-bar">
                <div class="toner-level ${cyanClass}" style="width: ${cyanPercent}%">
                    ${cyanPercent}%
                </div>
            </div>
            <div class="toner-bar">
                <div class="toner-level ${magentaClass}" style="width: ${magentaPercent}%">
                    ${magentaPercent}%
                </div>
            </div>
            <div class="toner-bar">
                <div class="toner-level ${yellowClass}" style="width: ${yellowPercent}%">
                    ${yellowPercent}%
                </div>
            </div>
        `;
    }
    
    return html;
}

// 장치 상세 정보 표시
function showDeviceDetails(ip) {
    // 모달 열기
    const modal = new bootstrap.Modal(document.getElementById('deviceModal'));
    modal.show();
    
    // 모달 제목 설정
    document.getElementById('device-modal-title').textContent = `장치 상세 정보 (${ip})`;
    
    // 로딩 표시
    document.getElementById('device-modal-body').innerHTML = `
        <div class="text-center py-5">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">로딩 중...</span>
            </div>
            <p class="mt-2">장치 정보를 불러오는 중입니다...</p>
        </div>
    `;
    
    // 웹 인터페이스 버튼 설정
    const webInterfaceBtn = document.getElementById('device-web-interface');
    webInterfaceBtn.onclick = function() {
        window.open(`http://${ip}`, '_blank');
    };
    
    // API 호출
    fetch(`/api/device/${ip}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayDeviceDetails(data.device);
            } else {
                document.getElementById('device-modal-body').innerHTML = `
                    <div class="alert alert-danger">
                        ${data.message}
                    </div>
                `;
            }
        })
        .catch(error => {
            document.getElementById('device-modal-body').innerHTML = `
                <div class="alert alert-danger">
                    장치 정보를 불러오는 중 오류가 발생했습니다: ${error.message}
                </div>
            `;
        });
}

// 장치 상세 정보 표시
function displayDeviceDetails(device) {
    // 토너 차트 데이터
    const tonerData = {
        labels: ['검정', '시안', '마젠타', '옐로우'],
        datasets: [{
            label: '토너 잔량 (%)',
            data: [
                device.toner.black.percent,
                device.toner.cyan.percent,
                device.toner.magenta.percent,
                device.toner.yellow.percent
            ],
            backgroundColor: [
                '#343a40',
                '#17a2b8',
                '#e83e8c',
                '#ffc107'
            ],
            borderWidth: 1
        }]
    };
    
    // 모달 내용 생성
    const modalBody = document.getElementById('device-modal-body');
    modalBody.innerHTML = `
        <div class="row">
            <div class="col-md-6">
                <div class="device-info">
                    <h5>기본 정보</h5>
                    <div class="info-item">
                        <div class="row">
                            <div class="col-5 info-label">상태</div>
                            <div class="col-7">${device.status}</div>
                        </div>
                    </div>
                    <div class="info-item">
                        <div class="row">
                            <div class="col-5 info-label">모델명</div>
                            <div class="col-7">${device.model}</div>
                        </div>
                    </div>
                    <div class="info-item">
                        <div class="row">
                            <div class="col-5 info-label">시리얼 번호</div>
                            <div class="col-7">${device.serial}</div>
                        </div>
                    </div>
                    <div class="info-item">
                        <div class="row">
                            <div class="col-5 info-label">IP 주소</div>
                            <div class="col-7">${device.ip}</div>
                        </div>
                    </div>
                    <div class="info-item">
                        <div class="row">
                            <div class="col-5 info-label">위치</div>
                            <div class="col-7">${device.location}</div>
                        </div>
                    </div>
                    <div class="info-item">
                        <div class="row">
                            <div class="col-5 info-label">담당자</div>
                            <div class="col-7">${device.contact}</div>
                        </div>
                    </div>
                    <div class="info-item">
                        <div class="row">
                            <div class="col-5 info-label">업타임</div>
                            <div class="col-7">${device.uptime}</div>
                        </div>
                    </div>
                    <div class="info-item">
                        <div class="row">
                            <div class="col-5 info-label">페이지 수</div>
                            <div class="col-7">${device.page_count.toLocaleString()}</div>
                        </div>
                    </div>
                    <div class="info-item">
                        <div class="row">
                            <div class="col-5 info-label">마지막 업데이트</div>
                            <div class="col-7">${device.last_update}</div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="device-info">
                    <h5>토너 상태</h5>
                    <div class="chart-container">
                        <canvas id="toner-chart"></canvas>
                    </div>
                    <div class="toner-details">
                        <div class="info-item">
                            <div class="row">
                                <div class="col-5 info-label">검정 토너</div>
                                <div class="col-7">${device.toner.black.level} / ${device.toner.black.max} (${device.toner.black.percent}%)</div>
                            </div>
                        </div>
                        <div class="info-item">
                            <div class="row">
                                <div class="col-5 info-label">시안 토너</div>
                                <div class="col-7">${device.toner.cyan.level} / ${device.toner.cyan.max} (${device.toner.cyan.percent}%)</div>
                            </div>
                        </div>
                        <div class="info-item">
                            <div class="row">
                                <div class="col-5 info-label">마젠타 토너</div>
                                <div class="col-7">${device.toner.magenta.level} / ${device.toner.magenta.max} (${device.toner.magenta.percent}%)</div>
                            </div>
                        </div>
                        <div class="info-item">
                            <div class="row">
                                <div class="col-5 info-label">옐로우 토너</div>
                                <div class="col-7">${device.toner.yellow.level} / ${device.toner.yellow.max} (${device.toner.yellow.percent}%)</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // 토너 차트 생성
    const ctx = document.getElementById('toner-chart').getContext('2d');
    new Chart(ctx, {
        type: 'bar',
        data: tonerData,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100
                }
            }
        }
    });
}

// 장치 필터링
function filterDevices() {
    const searchTerm = document.getElementById('search-input').value.toLowerCase();
    
    // 필터링된 장치 목록
    const filteredDevices = devices.filter(device => {
        // 검색어 필터
        if (searchTerm && !device.name.toLowerCase().includes(searchTerm) && 
            !device.model.toLowerCase().includes(searchTerm) && 
            !device.ip.toLowerCase().includes(searchTerm)) {
            return false;
        }
        
        return true;
    });
    
    // 필터링된 장치 표시
    displayDevices(filteredDevices);
}

// Excel로 내보내기
function exportToExcel() {
    // 현재 표시된 장치 목록 가져오기
    const rows = document.querySelectorAll('#devices-list tr');
    
    // 데이터가 없는 경우
    if (rows.length === 0 || (rows.length === 1 && rows[0].cells.length === 1)) {
        alert('내보낼 데이터가 없습니다.');
        return;
    }
    
    // CSV 데이터 생성
    let csv = '상태,번호,설치장소,모델명,시리얼 번호,IP 주소,토너 상태(검정),토너 상태(시안),토너 상태(마젠타),토너 상태(옐로우),페이지 수\n';
    
    // 각 장치에 대한 CSV 행 생성
    devices.forEach((device, index) => {
        const status = device.status;
        const name = device.name.replace(/,/g, ' ');
        const model = device.model.replace(/,/g, ' ');
        const serial = device.serial.replace(/,/g, ' ');
        const ip = device.ip;
        const blackToner = device.toner.black.percent;
        const cyanToner = device.toner.cyan.percent;
        const magentaToner = device.toner.magenta.percent;
        const yellowToner = device.toner.yellow.percent;
        const pageCount = device.page_count;
        
        csv += `${status},${index + 1},${name},${model},${serial},${ip},${blackToner}%,${cyanToner}%,${magentaToner}%,${yellowToner}%,${pageCount}\n`;
    });
    
    // CSV 파일 다운로드
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    
    link.setAttribute('href', url);
    link.setAttribute('download', `printer_scanner_${new Date().toISOString().slice(0, 10)}.csv`);
    link.style.visibility = 'hidden';
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// 오류 메시지 표시
function showError(message) {
    const alertDiv = document.createElement('div');
    alertDiv.className = 'alert alert-danger alert-dismissible fade show';
    alertDiv.innerHTML = `
        <i class="bi bi-exclamation-triangle-fill me-2"></i>${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    const container = document.querySelector('.container');
    container.insertBefore(alertDiv, container.firstChild);
    
    // 8초 후 자동으로 닫기
    setTimeout(() => {
        alertDiv.classList.remove('show');
        setTimeout(() => alertDiv.remove(), 300);
    }, 8000);
}

// 성공 메시지 표시
function showSuccess(message) {
    const alertDiv = document.createElement('div');
    alertDiv.className = 'alert alert-success alert-dismissible fade show';
    alertDiv.innerHTML = `
        <i class="bi bi-check-circle-fill me-2"></i>${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    const container = document.querySelector('.container');
    container.insertBefore(alertDiv, container.firstChild);
    
    // 5초 후 자동으로 닫기
    setTimeout(() => {
        alertDiv.classList.remove('show');
        setTimeout(() => alertDiv.remove(), 300);
    }, 5000);
}

// 정보 메시지 표시
function showInfo(message) {
    const alertDiv = document.createElement('div');
    alertDiv.className = 'alert alert-info alert-dismissible fade show';
    alertDiv.innerHTML = `
        <i class="bi bi-info-circle-fill me-2"></i>${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    const container = document.querySelector('.container');
    container.insertBefore(alertDiv, container.firstChild);
    
    // 5초 후 자동으로 닫기
    setTimeout(() => {
        alertDiv.classList.remove('show');
        setTimeout(() => alertDiv.remove(), 300);
    }, 5000);
} 