// 전역 변수
let devices = [];
let autoScanInterval = null;
let settings = {
    networkRange: '192.168.0.0/24',
    scanInterval: 300,
    snmpCommunity: 'public',
    snmpVersion: 2,
    autoScan: true
};

// DOM이 로드된 후 실행
document.addEventListener('DOMContentLoaded', function() {
    // 설정 로드
    loadSettings();
    
    // 이벤트 리스너 등록
    document.getElementById('scan-btn').addEventListener('click', startScan);
    document.getElementById('refresh-btn').addEventListener('click', startScan);
    document.getElementById('save-settings').addEventListener('click', saveSettings);
    document.getElementById('export-btn').addEventListener('click', exportToExcel);
    document.getElementById('search-input').addEventListener('input', filterDevices);
    document.getElementById('location-filter').addEventListener('input', filterDevices);
    document.getElementById('ip-filter').addEventListener('input', filterDevices);
    document.getElementById('toner-filter').addEventListener('change', filterDevices);
    document.getElementById('show-offline').addEventListener('change', filterDevices);
    document.getElementById('show-warning').addEventListener('change', filterDevices);
    
    // 자동 스캔 시작
    if (settings.autoScan) {
        startAutoScan();
    }
    
    // 초기 스캔 시작
    startScan();
});

// 설정 로드
function loadSettings() {
    const savedSettings = localStorage.getItem('printerScannerSettings');
    if (savedSettings) {
        settings = JSON.parse(savedSettings);
    }
    
    // 설정 폼에 값 설정
    document.getElementById('network-range').value = settings.networkRange;
    document.getElementById('scan-interval').value = settings.scanInterval;
    document.getElementById('snmp-community').value = settings.snmpCommunity;
    document.getElementById('snmp-version').value = settings.snmpVersion;
    document.getElementById('auto-scan').checked = settings.autoScan;
}

// 설정 저장
function saveSettings() {
    // 폼에서 값 가져오기
    settings.networkRange = document.getElementById('network-range').value;
    settings.scanInterval = parseInt(document.getElementById('scan-interval').value);
    settings.snmpCommunity = document.getElementById('snmp-community').value;
    settings.snmpVersion = parseInt(document.getElementById('snmp-version').value);
    settings.autoScan = document.getElementById('auto-scan').checked;
    
    // 로컬 스토리지에 저장
    localStorage.setItem('printerScannerSettings', JSON.stringify(settings));
    
    // 자동 스캔 설정 업데이트
    if (settings.autoScan) {
        startAutoScan();
    } else {
        stopAutoScan();
    }
    
    // 모달 닫기
    const modal = bootstrap.Modal.getInstance(document.getElementById('settingsModal'));
    modal.hide();
    
    // 스캔 시작
    startScan();
}

// 자동 스캔 시작
function startAutoScan() {
    // 기존 인터벌 정리
    stopAutoScan();
    
    // 새 인터벌 설정
    autoScanInterval = setInterval(startScan, settings.scanInterval * 1000);
}

// 자동 스캔 중지
function stopAutoScan() {
    if (autoScanInterval) {
        clearInterval(autoScanInterval);
        autoScanInterval = null;
    }
}

// 스캔 시작
function startScan() {
    // 로딩 표시
    document.getElementById('devices-list').innerHTML = `
        <tr>
            <td colspan="8" class="text-center py-5">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">로딩 중...</span>
                </div>
                <p class="mt-2">장치를 스캔하는 중입니다...</p>
            </td>
        </tr>
    `;
    
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
            network_range: settings.networkRange
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            devices = data.devices;
            displayDevices(devices);
        } else {
            showError(data.message);
        }
    })
    .catch(error => {
        showError('스캔 중 오류가 발생했습니다: ' + error.message);
    })
    .finally(() => {
        // 스캔 버튼 활성화
        scanBtn.disabled = false;
        scanBtn.innerHTML = '<i class="bi bi-search me-1"></i>스캔 시작';
    });
}

// 장치 목록 표시
function displayDevices(devicesList) {
    const tbody = document.getElementById('devices-list');
    
    // 장치가 없는 경우
    if (devicesList.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center py-5">
                    <i class="bi bi-exclamation-circle text-muted" style="font-size: 2rem;"></i>
                    <p class="mt-2">발견된 장치가 없습니다.</p>
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
        
        if (device.status.toLowerCase() === 'offline') {
            statusClass = 'status-offline';
            statusText = '오프라인';
        } else if (device.status.toLowerCase() === 'warning') {
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
                <td>${device.name}</td>
                <td>${device.model}</td>
                <td>${device.serial}</td>
                <td>${device.ip}</td>
                <td>${tonerHtml}</td>
                <td>${device.page_count.toLocaleString()}</td>
            </tr>
        `;
    });
    
    tbody.innerHTML = html;
    
    // 행 클릭 이벤트 등록
    document.querySelectorAll('.clickable-row').forEach(row => {
        row.addEventListener('click', function() {
            const ip = this.getAttribute('data-ip');
            showDeviceDetails(ip);
        });
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
    const locationFilter = document.getElementById('location-filter').value.toLowerCase();
    const ipFilter = document.getElementById('ip-filter').value.toLowerCase();
    const tonerFilter = document.getElementById('toner-filter').value;
    const showOffline = document.getElementById('show-offline').checked;
    const showWarning = document.getElementById('show-warning').checked;
    
    // 필터링된 장치 목록
    const filteredDevices = devices.filter(device => {
        // 검색어 필터
        if (searchTerm && !device.name.toLowerCase().includes(searchTerm) && 
            !device.model.toLowerCase().includes(searchTerm) && 
            !device.ip.toLowerCase().includes(searchTerm)) {
            return false;
        }
        
        // 위치 필터
        if (locationFilter && !device.name.toLowerCase().includes(locationFilter)) {
            return false;
        }
        
        // IP 필터
        if (ipFilter && !device.ip.toLowerCase().includes(ipFilter)) {
            return false;
        }
        
        // 상태 필터
        if (!showOffline && device.status.toLowerCase() === 'offline') {
            return false;
        }
        
        if (!showWarning && device.status.toLowerCase() === 'warning') {
            return false;
        }
        
        // 토너 필터
        if (tonerFilter) {
            const blackPercent = device.toner.black.percent;
            
            if (tonerFilter === 'low' && blackPercent > 20) {
                return false;
            } else if (tonerFilter === 'medium' && (blackPercent <= 20 || blackPercent > 50)) {
                return false;
            } else if (tonerFilter === 'high' && blackPercent <= 50) {
                return false;
            }
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

// 오류 표시
function showError(message) {
    const tbody = document.getElementById('devices-list');
    tbody.innerHTML = `
        <tr>
            <td colspan="8" class="text-center py-5">
                <div class="alert alert-danger">
                    <i class="bi bi-exclamation-triangle-fill me-2"></i>
                    ${message}
                </div>
            </td>
        </tr>
    `;
} 