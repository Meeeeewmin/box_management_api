from fastapi import FastAPI, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, validator
from sqlalchemy import create_engine, Column, Integer, String, DateTime, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
from typing import Optional, List
import re
import os

# 데이터베이스 설정 - 실제 환경에 맞게 수정하세요
DATABASE_URL = "mysql+pymysql://edge_user:edge_password_2024!@localhost:3306/edge_computer_db"

# 데이터베이스 연결 설정
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # 연결 상태 확인
    pool_recycle=300,    # 연결 재활용 시간 (초)
    echo=False           # SQL 쿼리 로깅 (개발시에는 True로 설정 가능)
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 데이터베이스 모델
class EdgeComputer(Base):
    __tablename__ = "edge_computers"
    
    no = Column(Integer, primary_key=True, index=True, autoincrement=True)
    mac = Column(String(17), nullable=False, unique=True, index=True)  # MAC 주소 형식: XX:XX:XX:XX:XX:XX
    ip = Column(String(15), nullable=True)  # IP 주소 형식: XXX.XXX.XXX.XXX
    main = Column(String(255), nullable=False)  # 주요 정보
    process = Column(String(255), nullable=False)  # 프로세스 정보
    modifier = Column(String(100), nullable=False)  # 수정자
    notice = Column(String(500), nullable=True)  # 비고
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ModificationHistory(Base):
    __tablename__ = "modification_history"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    computer_no = Column(Integer, nullable=False, index=True)  # 수정된 컴퓨터 번호
    action = Column(String(20), nullable=False)  # CREATE, UPDATE, DELETE
    field_name = Column(String(50), nullable=True)  # 수정된 필드명 (UPDATE시)
    old_value = Column(String(500), nullable=True)  # 이전 값
    new_value = Column(String(500), nullable=True)  # 새로운 값
    modifier = Column(String(100), nullable=False)  # 수정한 사람
    modified_at = Column(DateTime, default=datetime.utcnow)
    description = Column(String(500), nullable=True)  # 수정 설명

# Pydantic 모델
class EdgeComputerBase(BaseModel):
    mac: str
    ip: Optional[str] = None
    main: str
    process: str
    modifier: str
    notice: Optional[str] = None
    
    @validator('mac')
    def validate_mac(cls, v):
        if not re.match(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$', v):
            raise ValueError('MAC 주소 형식이 올바르지 않습니다. (예: AA:BB:CC:DD:EE:FF)')
        return v.upper()
    
    @validator('ip')
    def validate_ip(cls, v):
        if v and not re.match(r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$', v):
            raise ValueError('IP 주소 형식이 올바르지 않습니다. (예: 192.168.1.1)')
        return v

class EdgeComputerCreate(EdgeComputerBase):
    pass

class EdgeComputerUpdate(BaseModel):
    mac: Optional[str] = None
    ip: Optional[str] = None
    main: Optional[str] = None
    process: Optional[str] = None
    modifier: Optional[str] = None
    notice: Optional[str] = None
    
    @validator('mac')
    def validate_mac(cls, v):
        if v and not re.match(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$', v):
            raise ValueError('MAC 주소 형식이 올바르지 않습니다.')
        return v.upper() if v else v
    
    @validator('ip')
    def validate_ip(cls, v):
        if v and not re.match(r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$', v):
            raise ValueError('IP 주소 형식이 올바르지 않습니다.')
        return v

class EdgeComputerResponse(EdgeComputerBase):
    no: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ModificationHistoryResponse(BaseModel):
    id: int
    computer_no: int
    action: str
    field_name: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    modifier: str
    modified_at: datetime
    description: Optional[str] = None
    
    class Config:
        from_attributes = True

# FastAPI 앱 설정
app = FastAPI(title="Edge Computer 관리 시스템", description="Edge Computer 관리를 위한 API")

# 데이터베이스 의존성
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 데이터베이스 테이블 생성
Base.metadata.create_all(bind=engine)

# 수정 이력 저장 함수
def save_modification_history(db: Session, computer_no: int, action: str, modifier: str, 
                            field_name: str = None, old_value: str = None, new_value: str = None, 
                            description: str = None):
    """수정 이력을 저장합니다"""
    history = ModificationHistory(
        computer_no=computer_no,
        action=action,
        field_name=field_name,
        old_value=old_value,
        new_value=new_value,
        modifier=modifier,
        description=description
    )
    db.add(history)

# API 엔드포인트
# Favicon 처리
@app.get("/favicon.ico")
async def favicon():
    """파비콘 요청 처리"""
    return {"message": "No favicon"}

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """메인 웹 인터페이스"""
    html_content = """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Edge Computer 관리 시스템</title>
        <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🖥️</text></svg>">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/tailwindcss/2.2.19/tailwind.min.css" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
        <style>
            .gradient-bg {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            }
            .card-hover {
                transition: all 0.3s ease;
            }
            .card-hover:hover {
                transform: translateY(-5px);
                box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
            }
        </style>
    </head>
    <body class="bg-gray-100 min-h-screen">
        <div class="gradient-bg text-white py-6 mb-8">
            <div class="container mx-auto px-6">
                <h1 class="text-3xl font-bold flex items-center">
                    <i class="fas fa-server mr-3"></i>
                    Edge Computer 관리 시스템
                </h1>
                <p class="mt-2 text-blue-100">간편한 Edge Computer 관리 도구</p>
            </div>
        </div>
        
        <div class="container mx-auto px-6">
            <!-- 등록 폼 -->
            <div class="bg-white rounded-lg shadow-lg p-6 mb-8 card-hover">
                <h2 class="text-xl font-semibold mb-4 flex items-center">
                    <i class="fas fa-plus-circle text-green-500 mr-2"></i>
                    새 Edge Computer 등록
                </h2>
                <form id="computerForm" class="space-y-4">
                    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">MAC 주소 *</label>
                            <input type="text" id="mac" placeholder="AA:BB:CC:DD:EE:FF" required
                                   class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">IP 주소</label>
                            <input type="text" id="ip" placeholder="192.168.1.100" 
                                   class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">메인 정보 *</label>
                            <input type="text" id="main" placeholder="Edge Computer 01" required
                                   class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">프로세스 *</label>
                            <input type="text" id="process" placeholder="데이터 수집" required
                                   class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">수정자 *</label>
                            <input type="text" id="modifier" placeholder="홍길동" required
                                   class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">비고</label>
                            <input type="text" id="notice" placeholder="추가 정보" 
                                   class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent">
                        </div>
                    </div>
                    <div class="flex space-x-3">
                        <button type="submit" class="bg-blue-500 hover:bg-blue-600 text-white px-6 py-2 rounded-md transition duration-200">
                            <i class="fas fa-save mr-2"></i>등록
                        </button>
                        <button type="button" onclick="clearForm()" class="bg-gray-500 hover:bg-gray-600 text-white px-6 py-2 rounded-md transition duration-200">
                            <i class="fas fa-eraser mr-2"></i>초기화
                        </button>
                    </div>
                </form>
            </div>

            <!-- 검색 -->
            <div class="bg-white rounded-lg shadow-lg p-6 mb-8 card-hover">
                <h2 class="text-xl font-semibold mb-4 flex items-center">
                    <i class="fas fa-search text-blue-500 mr-2"></i>
                    검색
                </h2>
                <div class="flex space-x-3">
                    <input type="text" id="searchInput" placeholder="MAC, IP, 메인 정보, 프로세스로 검색..." 
                           class="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent">
                    <button onclick="searchComputers()" class="bg-blue-500 hover:bg-blue-600 text-white px-6 py-2 rounded-md transition duration-200">
                        검색
                    </button>
                    <button onclick="loadComputers()" class="bg-gray-500 hover:bg-gray-600 text-white px-6 py-2 rounded-md transition duration-200">
                        전체보기
                    </button>
                </div>
            </div>

            <!-- 컴퓨터 목록 -->
            <div class="bg-white rounded-lg shadow-lg overflow-hidden card-hover">
                <div class="px-6 py-4 bg-gray-50 border-b">
                    <h2 class="text-xl font-semibold flex items-center">
                        <i class="fas fa-list text-purple-500 mr-2"></i>
                        Edge Computer 목록
                    </h2>
                </div>
                <div class="overflow-x-auto">
                    <table class="w-full">
                        <thead class="bg-gray-50">
                            <tr>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">No</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">MAC</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">IP</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">메인</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">프로세스</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">수정자</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">비고</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">수정일</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">작업</th>
                            </tr>
                        </thead>
                        <tbody id="computerList" class="bg-white divide-y divide-gray-200">
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- 수정 모달 -->
        <div id="editModal" class="fixed inset-0 bg-gray-600 bg-opacity-50 hidden items-center justify-center z-50">
            <div class="bg-white rounded-lg shadow-lg p-6 w-full max-w-2xl mx-4">
                <h3 class="text-lg font-semibold mb-4">Edge Computer 수정</h3>
                <form id="editForm" class="space-y-4">
                    <input type="hidden" id="editNo">
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">MAC 주소 *</label>
                            <input type="text" id="editMac" required class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">IP 주소</label>
                            <input type="text" id="editIp" class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">메인 정보 *</label>
                            <input type="text" id="editMain" required class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">프로세스 *</label>
                            <input type="text" id="editProcess" required class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">수정자 *</label>
                            <input type="text" id="editModifier" required class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">비고</label>
                            <input type="text" id="editNotice" class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent">
                        </div>
                    </div>
                    <div class="flex space-x-3 pt-4">
                        <button type="submit" class="bg-blue-500 hover:bg-blue-600 text-white px-6 py-2 rounded-md transition duration-200">
                            <i class="fas fa-save mr-2"></i>수정
                        </button>
                        <button type="button" onclick="closeEditModal()" class="bg-gray-500 hover:bg-gray-600 text-white px-6 py-2 rounded-md transition duration-200">
                            취소
                        </button>
                    </div>
                </form>
            </div>
        </div>

        <!-- 이력 모달 -->
        <div id="historyModal" class="fixed inset-0 bg-gray-600 bg-opacity-50 hidden items-center justify-center z-50">
            <div class="bg-white rounded-lg shadow-lg p-6 w-full max-w-4xl mx-4 max-h-96">
                <div class="flex justify-between items-center mb-4">
                    <h3 class="text-lg font-semibold">수정 이력</h3>
                    <button onclick="closeHistoryModal()" class="text-gray-500 hover:text-gray-700">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="overflow-y-auto max-h-80">
                    <table class="w-full text-sm">
                        <thead class="bg-gray-50">
                            <tr>
                                <th class="px-3 py-2 text-left">날짜</th>
                                <th class="px-3 py-2 text-left">작업</th>
                                <th class="px-3 py-2 text-left">필드</th>
                                <th class="px-3 py-2 text-left">이전값</th>
                                <th class="px-3 py-2 text-left">새값</th>
                                <th class="px-3 py-2 text-left">수정자</th>
                            </tr>
                        </thead>
                        <tbody id="historyList" class="divide-y divide-gray-200">
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <script>
            let editingId = null;

            // 토스트 메시지 표시 함수
            function showToast(message, type = 'success') {
                const toast = document.createElement('div');
                toast.className = `fixed top-4 right-4 px-6 py-3 rounded-lg text-white font-medium z-50 transition-all duration-300 transform translate-x-full`;
                toast.className += type === 'success' ? ' bg-green-500' : ' bg-red-500';
                toast.textContent = message;
                
                document.body.appendChild(toast);
                
                // 애니메이션으로 표시
                setTimeout(() => {
                    toast.classList.remove('translate-x-full');
                }, 100);
                
                // 3초 후 제거
                setTimeout(() => {
                    toast.classList.add('translate-x-full');
                    setTimeout(() => {
                        document.body.removeChild(toast);
                    }, 300);
                }, 3000);
            }

            // 페이지 로드시 데이터 불러오기
            document.addEventListener('DOMContentLoaded', function() {
                loadComputers();
            });

            // 새 컴퓨터 등록
            document.getElementById('computerForm').addEventListener('submit', async function(e) {
                e.preventDefault();
                
                // 필수 필드 검증
                const mac = document.getElementById('mac').value.trim();
                const main = document.getElementById('main').value.trim();
                const process = document.getElementById('process').value.trim();
                const modifier = document.getElementById('modifier').value.trim();
                const ip = document.getElementById('ip').value.trim();
                
                // 필수 필드 체크
                if (!mac) {
                    alert('MAC 주소를 입력해주세요.');
                    document.getElementById('mac').focus();
                    return;
                }
                if (!main) {
                    alert('메인 정보를 입력해주세요.');
                    document.getElementById('main').focus();
                    return;
                }
                if (!process) {
                    alert('프로세스를 입력해주세요.');
                    document.getElementById('process').focus();
                    return;
                }
                if (!modifier) {
                    alert('수정자를 입력해주세요.');
                    document.getElementById('modifier').focus();
                    return;
                }
                
                const data = {
                    mac: mac,
                    ip: ip || null,
                    main: main,
                    process: process,
                    modifier: modifier,
                    notice: document.getElementById('notice').value.trim() || null
                };

                try {
                    const response = await fetch('/computers/', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(data)
                    });

                    if (response.ok) {
                        alert('등록되었습니다!');
                        clearForm();
                        loadComputers();
                    } else {
                        const error = await response.json();
                        // 오류 메시지를 더 자세히 표시
                        let errorMessage = '등록 중 오류가 발생했습니다.';
                        
                        if (error.detail) {
                            if (typeof error.detail === 'string') {
                                errorMessage = error.detail;
                            } else if (Array.isArray(error.detail)) {
                                errorMessage = error.detail.map(e => e.msg || e.message || JSON.stringify(e)).join('\n');
                            } else {
                                errorMessage = JSON.stringify(error.detail);
                            }
                        }
                        
                        alert(`오류: ${errorMessage}`);
                    }
                } catch (error) {
                    alert(`네트워크 오류: ${error.message}`);
                }
            });

            // 수정 폼 제출
            document.getElementById('editForm').addEventListener('submit', async function(e) {
                e.preventDefault();
                
                const no = document.getElementById('editNo').value;
                
                // 필수 필드 검증
                const mac = document.getElementById('editMac').value.trim();
                const main = document.getElementById('editMain').value.trim();
                const process = document.getElementById('editProcess').value.trim();
                const modifier = document.getElementById('editModifier').value.trim();
                const ip = document.getElementById('editIp').value.trim();
                
                // 필수 필드 체크
                if (!mac) {
                    alert('MAC 주소를 입력해주세요.');
                    document.getElementById('editMac').focus();
                    return;
                }
                if (!main) {
                    alert('메인 정보를 입력해주세요.');
                    document.getElementById('editMain').focus();
                    return;
                }
                if (!process) {
                    alert('프로세스를 입력해주세요.');
                    document.getElementById('editProcess').focus();
                    return;
                }
                if (!modifier) {
                    alert('수정자를 입력해주세요.');
                    document.getElementById('editModifier').focus();
                    return;
                }
                
                const data = {
                    mac: mac,
                    ip: ip || null,
                    main: main,
                    process: process,
                    modifier: modifier,
                    notice: document.getElementById('editNotice').value.trim() || null
                };

                try {
                    const response = await fetch(`/computers/${no}`, {
                        method: 'PUT',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(data)
                    });

                    if (response.ok) {
                        alert('수정되었습니다!');
                        closeEditModal();
                        loadComputers();
                    } else {
                        const error = await response.json();
                        // 오류 메시지를 더 자세히 표시
                        let errorMessage = '수정 중 오류가 발생했습니다.';
                        
                        if (error.detail) {
                            if (typeof error.detail === 'string') {
                                errorMessage = error.detail;
                            } else if (Array.isArray(error.detail)) {
                                errorMessage = error.detail.map(e => e.msg || e.message || JSON.stringify(e)).join('\n');
                            } else {
                                errorMessage = JSON.stringify(error.detail);
                            }
                        }
                        
                        alert(`오류: ${errorMessage}`);
                    }
                } catch (error) {
                    alert(`네트워크 오류: ${error.message}`);
                }
            });

            // 폼 초기화
            function clearForm() {
                document.getElementById('computerForm').reset();
            }

            // 컴퓨터 목록 불러오기
            async function loadComputers() {
                try {
                    const response = await fetch('/computers/');
                    const computers = await response.json();
                    displayComputers(computers);
                } catch (error) {
                    alert(`데이터 로드 오류: ${error.message}`);
                }
            }

            // 컴퓨터 검색
            async function searchComputers() {
                const query = document.getElementById('searchInput').value;
                if (!query) {
                    loadComputers();
                    return;
                }

                try {
                    const response = await fetch(`/computers/search?q=${encodeURIComponent(query)}`);
                    const computers = await response.json();
                    displayComputers(computers);
                } catch (error) {
                    alert(`검색 오류: ${error.message}`);
                }
            }

            // Enter 키로 검색
            document.getElementById('searchInput').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    searchComputers();
                }
            });

            // 컴퓨터 목록 표시
            function displayComputers(computers) {
                const tbody = document.getElementById('computerList');
                tbody.innerHTML = '';

                if (computers.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="9" class="px-6 py-4 text-center text-gray-500">데이터가 없습니다.</td></tr>';
                    return;
                }

                computers.forEach(computer => {
                    const row = document.createElement('tr');
                    row.className = 'hover:bg-gray-50';
                    row.innerHTML = `
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${computer.no}</td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 font-mono">${computer.mac}</td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 font-mono">${computer.ip || '-'}</td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${computer.main}</td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${computer.process}</td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${computer.modifier}</td>
                        <td class="px-6 py-4 text-sm text-gray-900">${computer.notice || '-'}</td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${new Date(computer.updated_at).toLocaleString('ko-KR')}</td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                            <button onclick="editComputer(${computer.no})" class="text-blue-600 hover:text-blue-900 mr-3" title="수정">
                                <i class="fas fa-edit"></i>
                            </button>
                            <button onclick="showHistory(${computer.no})" class="text-green-600 hover:text-green-900 mr-3" title="이력 보기">
                                <i class="fas fa-history"></i>
                            </button>
                            <button onclick="deleteComputer(${computer.no})" class="text-red-600 hover:text-red-900" title="삭제">
                                <i class="fas fa-trash"></i>
                            </button>
                        </td>
                    `;
                    tbody.appendChild(row);
                });
            }

            // 수정 모달 열기
            async function editComputer(no) {
                try {
                    const response = await fetch(`/computers/${no}`);
                    const computer = await response.json();
                    
                    document.getElementById('editNo').value = computer.no;
                    document.getElementById('editMac').value = computer.mac;
                    document.getElementById('editIp').value = computer.ip || '';
                    document.getElementById('editMain').value = computer.main;
                    document.getElementById('editProcess').value = computer.process;
                    document.getElementById('editModifier').value = computer.modifier;
                    document.getElementById('editNotice').value = computer.notice || '';
                    
                    document.getElementById('editModal').classList.remove('hidden');
                    document.getElementById('editModal').classList.add('flex');
                } catch (error) {
                    alert(`데이터 로드 오류: ${error.message}`);
                }
            }

            // 수정 모달 닫기
            function closeEditModal() {
                document.getElementById('editModal').classList.add('hidden');
                document.getElementById('editModal').classList.remove('flex');
            }

            // 삭제
            async function deleteComputer(no) {
                if (confirm('정말 삭제하시겠습니까?')) {
                    try {
                        const response = await fetch(`/computers/${no}`, {
                            method: 'DELETE'
                        });

                        if (response.ok) {
                            alert('삭제되었습니다!');
                            loadComputers();
                        } else {
                            alert('삭제 중 오류가 발생했습니다.');
                        }
                    } catch (error) {
                        alert(`네트워크 오류: ${error.message}`);
                    }
                }
            }

            // 이력 보기
            async function showHistory(no) {
                try {
                    const response = await fetch(`/computers/${no}/history`);
                    const history = await response.json();
                    
                    const tbody = document.getElementById('historyList');
                    tbody.innerHTML = '';
                    
                    if (history.length === 0) {
                        tbody.innerHTML = '<tr><td colspan="6" class="px-3 py-4 text-center text-gray-500">수정 이력이 없습니다.</td></tr>';
                    } else {
                        history.forEach(item => {
                            const row = document.createElement('tr');
                            row.className = 'hover:bg-gray-50';
                            
                            const actionText = {
                                'CREATE': '생성',
                                'UPDATE': '수정', 
                                'DELETE': '삭제'
                            }[item.action] || item.action;
                            
                            row.innerHTML = `
                                <td class="px-3 py-2">${new Date(item.modified_at).toLocaleString('ko-KR')}</td>
                                <td class="px-3 py-2">
                                    <span class="px-2 py-1 text-xs rounded-full ${
                                        item.action === 'CREATE' ? 'bg-green-100 text-green-800' :
                                        item.action === 'UPDATE' ? 'bg-blue-100 text-blue-800' :
                                        'bg-red-100 text-red-800'
                                    }">${actionText}</span>
                                </td>
                                <td class="px-3 py-2">${item.field_name || '-'}</td>
                                <td class="px-3 py-2 max-w-32 truncate" title="${item.old_value || ''}">${item.old_value || '-'}</td>
                                <td class="px-3 py-2 max-w-32 truncate" title="${item.new_value || ''}">${item.new_value || '-'}</td>
                                <td class="px-3 py-2">${item.modifier}</td>
                            `;
                            tbody.appendChild(row);
                        });
                    }
                    
                    document.getElementById('historyModal').classList.remove('hidden');
                    document.getElementById('historyModal').classList.add('flex');
                } catch (error) {
                    alert(`이력 조회 오류: ${error.message}`);
                }
            }

            // 이력 모달 닫기
            function closeHistoryModal() {
                document.getElementById('historyModal').classList.add('hidden');
                document.getElementById('historyModal').classList.remove('flex');
            }

            // 모달 배경 클릭시 닫기
            document.getElementById('editModal').addEventListener('click', function(e) {
                if (e.target === this) {
                    closeEditModal();
                }
            });

            // 이력 모달 배경 클릭시 닫기
            document.getElementById('historyModal').addEventListener('click', function(e) {
                if (e.target === this) {
                    closeHistoryModal();
                }
            });
        </script>
    </body>
    </html>
    """
    return html_content

@app.get("/computers/", response_model=List[EdgeComputerResponse])
def read_computers(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """모든 Edge Computer 조회"""
    computers = db.query(EdgeComputer).offset(skip).limit(limit).all()
    return computers

@app.get("/computers/search", response_model=List[EdgeComputerResponse])
def search_computers(q: str, db: Session = Depends(get_db)):
    """Edge Computer 검색"""
    computers = db.query(EdgeComputer).filter(
        (EdgeComputer.mac.contains(q)) |
        (EdgeComputer.ip.contains(q)) |
        (EdgeComputer.main.contains(q)) |
        (EdgeComputer.process.contains(q)) |
        (EdgeComputer.modifier.contains(q)) |
        (EdgeComputer.notice.contains(q))
    ).all()
    return computers

@app.get("/computers/{computer_id}", response_model=EdgeComputerResponse)
def read_computer(computer_id: int, db: Session = Depends(get_db)):
    """특정 Edge Computer 조회"""
    computer = db.query(EdgeComputer).filter(EdgeComputer.no == computer_id).first()
    if computer is None:
        raise HTTPException(status_code=404, detail="Edge Computer를 찾을 수 없습니다")
    return computer

@app.post("/computers/", response_model=EdgeComputerResponse)
def create_computer(computer: EdgeComputerCreate, db: Session = Depends(get_db)):
    """새 Edge Computer 등록"""
    # MAC 주소 중복 체크
    existing = db.query(EdgeComputer).filter(EdgeComputer.mac == computer.mac).first()
    if existing:
        raise HTTPException(status_code=400, detail="이미 존재하는 MAC 주소입니다")
    
    db_computer = EdgeComputer(**computer.dict())
    db.add(db_computer)
    db.commit()
    db.refresh(db_computer)
    
    # 생성 이력 저장
    save_modification_history(
        db, 
        db_computer.no, 
        "CREATE", 
        computer.modifier,
        description=f"새 Edge Computer 등록: MAC={computer.mac}, MAIN={computer.main}"
    )
    db.commit()
    
    return db_computer

@app.put("/computers/{computer_id}", response_model=EdgeComputerResponse)
def update_computer(computer_id: int, computer: EdgeComputerUpdate, db: Session = Depends(get_db)):
    """Edge Computer 정보 수정"""
    db_computer = db.query(EdgeComputer).filter(EdgeComputer.no == computer_id).first()
    if db_computer is None:
        raise HTTPException(status_code=404, detail="Edge Computer를 찾을 수 없습니다")
    
    # MAC 주소 중복 체크 (자신 제외)
    if computer.mac and computer.mac != db_computer.mac:
        existing = db.query(EdgeComputer).filter(EdgeComputer.mac == computer.mac).first()
        if existing:
            raise HTTPException(status_code=400, detail="이미 존재하는 MAC 주소입니다")
    
    # 변경 사항 추적
    update_data = computer.dict(exclude_unset=True)
    changes = []
    
    for field, new_value in update_data.items():
        if field == 'modifier':
            continue  # modifier는 변경 사항에서 제외
            
        old_value = getattr(db_computer, field)
        
        # 값이 실제로 변경된 경우만 기록
        if str(old_value) != str(new_value):
            changes.append({
                'field': field,
                'old_value': str(old_value) if old_value is not None else None,
                'new_value': str(new_value) if new_value is not None else None
            })
    
    # 데이터 업데이트
    for field, value in update_data.items():
        setattr(db_computer, field, value)
    
    db_computer.updated_at = datetime.utcnow()
    
    # 변경 이력 저장
    modifier = computer.modifier or "Unknown"
    for change in changes:
        save_modification_history(
            db,
            computer_id,
            "UPDATE",
            modifier,
            field_name=change['field'],
            old_value=change['old_value'],
            new_value=change['new_value'],
            description=f"{change['field']} 필드 변경"
        )
    
    db.commit()
    db.refresh(db_computer)
    return db_computer

@app.delete("/computers/{computer_id}")
def delete_computer(computer_id: int, db: Session = Depends(get_db)):
    """Edge Computer 삭제"""
    computer = db.query(EdgeComputer).filter(EdgeComputer.no == computer_id).first()
    if computer is None:
        raise HTTPException(status_code=404, detail="Edge Computer를 찾을 수 없습니다")
    
    # 삭제 이력 저장
    save_modification_history(
        db,
        computer_id,
        "DELETE",
        "System",  # 삭제시에는 시스템이 수행한 것으로 기록
        description=f"Edge Computer 삭제: MAC={computer.mac}, MAIN={computer.main}"
    )
    
    db.delete(computer)
    db.commit()
    return {"message": "Edge Computer가 삭제되었습니다"}

@app.get("/computers/{computer_id}/history", response_model=List[ModificationHistoryResponse])
def get_computer_history(computer_id: int, db: Session = Depends(get_db)):
    """특정 Edge Computer의 수정 이력 조회"""
    history = db.query(ModificationHistory).filter(
        ModificationHistory.computer_no == computer_id
    ).order_by(ModificationHistory.modified_at.desc()).all()
    return history

@app.get("/history", response_model=List[ModificationHistoryResponse])
def get_all_history(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """모든 수정 이력 조회"""
    history = db.query(ModificationHistory).order_by(
        ModificationHistory.modified_at.desc()
    ).offset(skip).limit(limit).all()
    return history

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
