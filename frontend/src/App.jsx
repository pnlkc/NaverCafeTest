import React, { useState, useEffect } from 'react';
import { 
  Settings, 
  Activity, 
  FileText, 
  RefreshCw, 
  UserCheck, 
  Bell, 
  BookOpen, 
  AlertCircle, 
  CheckCircle, 
  ExternalLink, 
  Save, 
  Plus, 
  X,
  ArrowRight,
  Shield,
  HelpCircle
} from 'lucide-react';

const API_BASE = window.location.hostname === 'localhost' ? 'http://localhost:8000' : '';

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [settings, setSettings] = useState(null);
  const [sessionStatus, setSessionStatus] = useState({ logged_in: false, message: '세션 확인 중...' });
  const [logs, setLogs] = useState([]);
  const [archives, setArchives] = useState([]);
  const [loading, setLoading] = useState(false);
  const [actionStatus, setActionStatus] = useState(null);
  
  // 모달 상태
  const [selectedArchive, setSelectedArchive] = useState(null);
  const [archiveHtml, setArchiveHtml] = useState('');

  // 설정 입력용 로컬 상태
  const [teamInput, setTeamInput] = useState('');
  const [keywordInput, setKeywordInput] = useState('');

  // 초기 데이터 로드
  useEffect(() => {
    fetchSettings();
    fetchSessionStatus();
    fetchLogs();
    fetchArchives();

    // 10초마다 세션 상태 및 로그 자동 갱신
    const interval = setInterval(() => {
      fetchSessionStatus();
      if (activeTab === 'dashboard') fetchLogs();
    }, 10000);

    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (activeTab === 'logs') {
      fetchLogs();
      fetchArchives();
    }
  }, [activeTab]);

  const fetchSettings = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/settings`);
      const data = await res.json();
      setSettings(data);
    } catch (e) {
      console.error('설정 로드 실패:', e);
    }
  };

  const fetchSessionStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/session/status`);
      const data = await res.json();
      setSessionStatus(data);
    } catch (e) {
      console.error('세션 상태 조회 실패:', e);
    }
  };

  const fetchLogs = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/logs?limit=30`);
      const data = await res.json();
      setLogs(data.items || []);
    } catch (e) {
      console.error('로그 조회 실패:', e);
    }
  };

  const fetchArchives = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/archives?limit=30`);
      const data = await res.json();
      setArchives(data.items || []);
    } catch (e) {
      console.error('아카이브 조회 실패:', e);
    }
  };

  const handleSaveSettings = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
      });
      const data = await res.json();
      if (data.status === 'SUCCESS') {
        showActionStatus('SUCCESS', '설정이 성공적으로 저장되었습니다.');
      } else {
        showActionStatus('FAILED', '설정 저장에 실패했습니다.');
      }
    } catch (error) {
      showActionStatus('FAILED', '네트워크 오류로 설정 저장 실패');
    } finally {
      setLoading(false);
    }
  };

  const handleTriggerLogin = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/session/login`, { method: 'POST' });
      const data = await res.json();
      showActionStatus('SUCCESS', '로그인 브라우저를 기동했습니다. 서버 PC의 화면을 확인하세요.');
      // 로그인 창 기동 후 잠시 후 세션 상태 조회
      setTimeout(fetchSessionStatus, 5000);
    } catch (error) {
      showActionStatus('FAILED', '로그인 실행 요청 실패');
    } finally {
      setLoading(false);
    }
  };

  const handleRunAction = async (actionPath, actionName) => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/action/${actionPath}`, { method: 'POST' });
      const data = await res.json();
      if (data.status === 'SUCCESS') {
        showActionStatus('SUCCESS', `${actionName} 작업이 성공적으로 실행되었습니다: ${data.message}`);
      } else {
        showActionStatus('FAILED', `${actionName} 작업 실행 실패: ${data.message}`);
      }
      fetchLogs();
    } catch (error) {
      showActionStatus('FAILED', `${actionName} 실행 중 네트워크 오류 발생`);
    } finally {
      setLoading(false);
    }
  };

  const showActionStatus = (type, message) => {
    setActionStatus({ type, message });
    setTimeout(() => setActionStatus(null), 5000);
  };

  const handleOpenArchive = async (archive) => {
    setSelectedArchive(archive);
    try {
      // 본문 HTML 가져오기
      const res = await fetch(`${API_BASE}/api/archives/${archive.article_id}/html`);
      if (res.ok) {
        let htmlText = await res.text();
        // 이미지 경로를 API 엔드포인트 주소로 변경하여 정상적으로 이미지 표시되도록 치환
        // 예: ./images/img_1.jpg -> http://localhost:8000/api/archives/{id}/images/img_1.jpg
        const imgApiUrl = `${API_BASE}/api/archives/${archive.article_id}/images/`;
        htmlText = htmlText.replace(/src="\.\/images\//g, `src="${imgApiUrl}`);
        setArchiveHtml(htmlText);
      } else {
        setArchiveHtml('<p style="color: var(--danger)">기사 본문을 불러오지 못했습니다.</p>');
      }
    } catch (error) {
      setArchiveHtml('<p style="color: var(--danger)">네트워크 오류로 본문을 불러올 수 없습니다.</p>');
    }
  };

  // 통계 계산
  const getStats = () => {
    // JOIN_APPROVE 성공 로그 메시지에서 승인된 실제 멤버 수 합산
    let joinCount = 0;
    logs.forEach(l => {
      if (l.action_type === 'JOIN_APPROVE' && l.status === 'SUCCESS') {
        const match = l.message.match(/회원\s*(\d+)명/);
        if (match) {
          joinCount += parseInt(match[1]);
        } else if (l.message.includes("승인 완료")) {
          // Fallback
          const numMatch = l.message.match(/(\d+)명/);
          if (numMatch) joinCount += parseInt(numMatch[1]);
        }
      }
    });

    // LEVEL_UP 성공 로그 메시지에서 등업된 실제 멤버 수 합산
    let levelupCount = 0;
    logs.forEach(l => {
      if (l.action_type === 'LEVEL_UP' && l.status === 'SUCCESS') {
        const match = l.message.match(/회원\s*(\d+)명/);
        if (match) {
          levelupCount += parseInt(match[1]);
        } else if (l.message.includes("등업 완료")) {
          // Fallback
          const numMatch = l.message.match(/(\d+)명/);
          if (numMatch) levelupCount += parseInt(numMatch[1]);
        }
      }
    });

    const counts = {
      join: joinCount,
      levelup: levelupCount,
      news: archives.length,
      errors: logs.filter(l => l.status === 'FAILED').length
    };
    return counts;
  };

  const stats = getStats();

  return (
    <div style={{ paddingBottom: '60px' }}>
      {/* 프리미엄 헤더 바 */}
      <header className="glass-panel" style={{ margin: '20px', padding: '16px 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--panel-border)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <Shield style={{ color: 'var(--primary)', width: '28px', height: '28px' }} />
          <div>
            <h1 className="primary-gradient-text" style={{ margin: 0, fontSize: '20px', fontWeight: 700 }}>NAVER CAFE MANAGER</h1>
            <p style={{ margin: 0, fontSize: '11px', color: 'var(--text-secondary)' }}>Automated Moderation & Esports News Archiving</p>
          </div>
        </div>

        {/* 탭 네비게이션 */}
        <nav style={{ display: 'flex', gap: '8px' }}>
          <button 
            className={`btn-secondary ${activeTab === 'dashboard' ? 'btn-primary' : ''}`}
            onClick={() => setActiveTab('dashboard')}
            style={activeTab === 'dashboard' ? { background: 'var(--primary)', border: 'none' } : {}}
          >
            <Activity size={16} /> 대시보드
          </button>
          <button 
            className={`btn-secondary ${activeTab === 'settings' ? 'btn-primary' : ''}`}
            onClick={() => setActiveTab('settings')}
            style={activeTab === 'settings' ? { background: 'var(--primary)', border: 'none' } : {}}
          >
            <Settings size={16} /> 설정 관리
          </button>
          <button 
            className={`btn-secondary ${activeTab === 'logs' ? 'btn-primary' : ''}`}
            onClick={() => setActiveTab('logs')}
            style={activeTab === 'logs' ? { background: 'var(--primary)', border: 'none' } : {}}
          >
            <FileText size={16} /> 작업 로그 & 뉴스 아카이브
          </button>
        </nav>
      </header>

      {/* 액션 상태 피드백 알림 배너 */}
      {actionStatus && (
        <div className="glass-panel" style={{
          margin: '0 20px 20px 20px',
          padding: '12px 20px',
          borderColor: actionStatus.type === 'SUCCESS' ? 'var(--success)' : 'var(--danger)',
          background: actionStatus.type === 'SUCCESS' ? 'rgba(0, 230, 118, 0.08)' : 'rgba(255, 23, 68, 0.08)',
          display: 'flex',
          alignItems: 'center',
          gap: '12px'
        }}>
          {actionStatus.type === 'SUCCESS' ? <CheckCircle color="var(--success)" size={20} /> : <AlertCircle color="var(--danger)" size={20} />}
          <span style={{ fontSize: '14px', fontWeight: 500 }}>{actionStatus.message}</span>
        </div>
      )}

      {/* 메인 뷰포트 */}
      <main style={{ padding: '0 20px' }}>
        
        {/* ==================== 1. 대시보드 탭 ==================== */}
        {activeTab === 'dashboard' && (
          <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '20px' }}>
            
            {/* 왼쪽 영역: 통계 카드 및 수동 액션 */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              
              {/* 통계 그리드 */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px' }}>
                <div className="glass-panel" style={{ padding: '20px', textAlign: 'center' }}>
                  <p style={{ margin: '0 0 8px 0', fontSize: '12px', color: 'var(--text-secondary)' }}>누적 가입 승인</p>
                  <h3 style={{ margin: 0, fontSize: '32px', fontWeight: 700, color: 'var(--success)' }}>{stats.join}</h3>
                </div>
                <div className="glass-panel" style={{ padding: '20px', textAlign: 'center' }}>
                  <p style={{ margin: '0 0 8px 0', fontSize: '12px', color: 'var(--text-secondary)' }}>자동 등업 완료</p>
                  <h3 style={{ margin: 0, fontSize: '32px', fontWeight: 700, color: 'var(--primary)' }}>{stats.levelup}</h3>
                </div>
                <div className="glass-panel" style={{ padding: '20px', textAlign: 'center' }}>
                  <p style={{ margin: '0 0 8px 0', fontSize: '12px', color: 'var(--text-secondary)' }}>뉴스 보관 건수</p>
                  <h3 style={{ margin: 0, fontSize: '32px', fontWeight: 700, color: 'var(--secondary)' }}>{stats.news}</h3>
                </div>
                <div className="glass-panel" style={{ padding: '20px', textAlign: 'center' }}>
                  <p style={{ margin: '0 0 8px 0', fontSize: '12px', color: 'var(--text-secondary)' }}>감지된 오류</p>
                  <h3 style={{ margin: 0, fontSize: '32px', fontWeight: 700, color: stats.errors > 0 ? 'var(--danger)' : 'var(--text-muted)' }}>{stats.errors}</h3>
                </div>
              </div>

              {/* 실시간 수동 실행 패널 */}
              <div className="glass-panel" style={{ padding: '24px' }}>
                <h3 className="gradient-text" style={{ margin: '0 0 16px 0', fontSize: '18px', fontWeight: 600 }}>즉시 제어 및 실행 (통합 API)</h3>
                <p style={{ fontSize: '13px', color: 'var(--text-secondary)', margin: '-10px 0 20px 0' }}>백그라운드 스케줄러와 별도로, 즉시 봇 조작 명령을 수동 송신합니다.</p>
                
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px' }}>
                  <button className="btn-secondary" onClick={() => handleRunAction('join-approve', '가입 승인')} style={{ padding: '16px', justifyContent: 'center' }}>
                    <UserCheck size={18} /> 가입 즉시 전체 승인
                  </button>
                  <button className="btn-secondary" onClick={() => handleRunAction('level-up', '자동 등업')} style={{ padding: '16px', justifyContent: 'center' }}>
                    <Shield size={18} /> 자동 등업 즉시 검사
                  </button>
                  <button className="btn-secondary" onClick={() => handleRunAction('news-publish', '뉴스 발행')} style={{ padding: '16px', justifyContent: 'center' }}>
                    <BookOpen size={18} /> 뉴스 즉시 크롤링 및 발행
                  </button>
                  <button className="btn-secondary" onClick={() => handleRunAction('test-discord', '디스코드 웹훅 테스트')} style={{ padding: '16px', justifyContent: 'center' }}>
                    <Bell size={18} /> 디스코드 알림 테스트 발송
                  </button>
                </div>
              </div>

              {/* 최근 로그 요약 */}
              <div className="glass-panel" style={{ padding: '24px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                  <h3 className="gradient-text" style={{ margin: 0, fontSize: '18px', fontWeight: 600 }}>최근 작동 로그 (실시간)</h3>
                  <button onClick={fetchLogs} className="btn-secondary" style={{ padding: '6px 12px', fontSize: '12px' }}>
                    <RefreshCw size={12} /> 새로고침
                  </button>
                </div>
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                    <thead>
                      <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', textAlign: 'left', color: 'var(--text-muted)' }}>
                        <th style={{ padding: '10px' }}>시간</th>
                        <th style={{ padding: '10px' }}>작업명</th>
                        <th style={{ padding: '10px' }}>상태</th>
                        <th style={{ padding: '10px' }}>메시지</th>
                      </tr>
                    </thead>
                    <tbody>
                      {logs.slice(0, 7).map((log) => (
                        <tr key={log.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                          <td style={{ padding: '10px', color: 'var(--text-muted)' }}>{log.created_at}</td>
                          <td style={{ padding: '10px' }}>
                            <span className="badge badge-success" style={{ background: 'rgba(255,255,255,0.05)', color: '#fff', border: '1px solid rgba(255,255,255,0.1)' }}>{log.action_type}</span>
                          </td>
                          <td style={{ padding: '10px' }}>
                            <span className={`badge ${log.status === 'SUCCESS' ? 'badge-success' : 'badge-danger'}`}>{log.status}</span>
                          </td>
                          <td style={{ padding: '10px', color: 'var(--text-secondary)' }}>{log.message}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

            </div>

            {/* 오른쪽 영역: 봇 세션 상태 및 수동 로그인 */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <div className="glass-panel" style={{ padding: '24px' }}>
                <h3 className="gradient-text" style={{ margin: '0 0 16px 0', fontSize: '18px', fontWeight: 600 }}>네이버 로그인 세션</h3>
                
                {/* 로그인 상태 카드 */}
                <div style={{ 
                  background: sessionStatus.logged_in ? 'rgba(0, 230, 118, 0.05)' : 'rgba(255, 23, 68, 0.05)', 
                  border: `1px solid ${sessionStatus.logged_in ? 'rgba(0, 230, 118, 0.2)' : 'rgba(255, 23, 68, 0.2)'}`,
                  borderRadius: '12px',
                  padding: '16px',
                  marginBottom: '20px'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                    <div style={{ 
                      width: '10px', 
                      height: '10px', 
                      borderRadius: '50%', 
                      background: sessionStatus.logged_in ? 'var(--success)' : 'var(--danger)',
                      boxShadow: `0 0 10px ${sessionStatus.logged_in ? 'var(--success)' : 'var(--danger)'}`
                    }}></div>
                    <span style={{ fontSize: '15px', fontWeight: 600 }}>
                      {sessionStatus.logged_in ? '로그인 세션 활성화' : '로그인 세션 만료/없음'}
                    </span>
                  </div>
                  <p style={{ margin: 0, fontSize: '12px', color: 'var(--text-secondary)' }}>
                    {sessionStatus.message}
                  </p>
                  {sessionStatus.updated_at && (
                    <p style={{ margin: '4px 0 0 0', fontSize: '11px', color: 'var(--text-muted)' }}>
                      최근 저장일: {sessionStatus.updated_at}
                    </p>
                  )}
                </div>

                <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '16px', lineHeight: '1.6' }}>
                  네이버 봇 방지 및 CAPTCHA 회피를 위해 최초 1회 수동 로그인이 필요합니다. 아래 버튼을 클릭하면 서버 PC에 로그인 브라우저(헤드풀)가 열립니다. 로그인 완료 후 브라우저가 자동 종료되며 세션이 안전하게 저장됩니다.
                </p>

                <button 
                  className="btn-primary" 
                  onClick={handleTriggerLogin} 
                  style={{ width: '100%', justifyContent: 'center', padding: '12px' }}
                  disabled={loading}
                >
                  <RefreshCw size={16} /> 최초 1회 로그인 세션 획득
                </button>
              </div>
            </div>

          </div>
        )}

        {/* ==================== 2. 설정 관리 탭 ==================== */}
        {activeTab === 'settings' && settings && (
          <form onSubmit={handleSaveSettings} className="glass-panel" style={{ padding: '32px', maxWidth: '900px', margin: '0 auto' }}>
            <h2 className="gradient-text" style={{ margin: '0 0 24px 0', fontSize: '22px', fontWeight: 700 }}>시스템 세부 설정</h2>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
              
              {/* 네이버 카페 기본 설정 */}
              <div>
                <h4 style={{ color: 'var(--primary)', margin: '0 0 12px 0', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '6px' }}>네이버 카페 설정</h4>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <label style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>카페 Club ID (고유번호)</label>
                    <input 
                      type="text" 
                      value={settings.cafe.club_id} 
                      onChange={e => setSettings({...settings, cafe: {...settings.cafe, club_id: e.target.value}})}
                      placeholder="예: 31234567"
                    />
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <label style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>관리자 네이버 ID</label>
                    <input 
                      type="text" 
                      value={settings.cafe.naver_id} 
                      onChange={e => setSettings({...settings, cafe: {...settings.cafe, naver_id: e.target.value}})}
                      placeholder="예: admin_id"
                    />
                  </div>
                </div>
              </div>

              {/* 각 모니터링 주기 설정 */}
              <div>
                <h4 style={{ color: 'var(--primary)', margin: '0 0 12px 0', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '6px' }}>기능별 실행 주기 (초 단위)</h4>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <label style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>가입 자동 승인</label>
                    <input 
                      type="number" 
                      value={settings.intervals.join_approve} 
                      onChange={e => setSettings({...settings, intervals: {...settings.intervals, join_approve: parseInt(e.target.value)}})}
                    />
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <label style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>자동 등업 검사</label>
                    <input 
                      type="number" 
                      value={settings.intervals.level_up} 
                      onChange={e => setSettings({...settings, intervals: {...settings.intervals, level_up: parseInt(e.target.value)}})}
                    />
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <label style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>신고 게시판 모니터링</label>
                    <input 
                      type="number" 
                      value={settings.intervals.report_alert} 
                      onChange={e => setSettings({...settings, intervals: {...settings.intervals, report_alert: parseInt(e.target.value)}})}
                    />
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <label style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>건의 사항 모니터링</label>
                    <input 
                      type="number" 
                      value={settings.intervals.suggestion_alert} 
                      onChange={e => setSettings({...settings, intervals: {...settings.intervals, suggestion_alert: parseInt(e.target.value)}})}
                    />
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <label style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>뉴스 수집 및 발행 (하루 86400)</label>
                    <input 
                      type="number" 
                      value={settings.intervals.news_publish} 
                      onChange={e => setSettings({...settings, intervals: {...settings.intervals, news_publish: parseInt(e.target.value)}})}
                    />
                  </div>
                </div>
              </div>

              {/* 등업 조건 설정 */}
              <div>
                <h4 style={{ color: 'var(--primary)', margin: '0 0 12px 0', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '6px' }}>자동 등업 조건 관리</h4>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px', marginBottom: '12px' }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <label style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>무작위 숫자 닉네임 최소 길이</label>
                    <input 
                      type="number" 
                      value={settings.levelup_conditions.min_nickname_length} 
                      onChange={e => setSettings({...settings, levelup_conditions: {...settings.levelup_conditions, min_nickname_length: parseInt(e.target.value)}})}
                    />
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <label style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>최소 방문 횟수</label>
                    <input 
                      type="number" 
                      value={settings.levelup_conditions.min_visit_count} 
                      onChange={e => setSettings({...settings, levelup_conditions: {...settings.levelup_conditions, min_visit_count: parseInt(e.target.value)}})}
                    />
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <label style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>최소 댓글 작성 수</label>
                    <input 
                      type="number" 
                      value={settings.levelup_conditions.min_comment_count} 
                      onChange={e => setSettings({...settings, levelup_conditions: {...settings.levelup_conditions, min_comment_count: parseInt(e.target.value)}})}
                    />
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <label style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>가입인사 게시판 이름</label>
                    <input 
                      type="text" 
                      value={settings.levelup_conditions.welcome_board_name} 
                      onChange={e => setSettings({...settings, levelup_conditions: {...settings.levelup_conditions, welcome_board_name: e.target.value}})}
                    />
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', height: '100%', paddingTop: '20px' }}>
                    <input 
                      type="checkbox" 
                      id="checkWelcome"
                      checked={settings.levelup_conditions.check_welcome_post} 
                      onChange={e => setSettings({...settings, levelup_conditions: {...settings.levelup_conditions, check_welcome_post: e.target.checked}})}
                      style={{ width: '18px', height: '18px', cursor: 'pointer' }}
                    />
                    <label htmlFor="checkWelcome" style={{ fontSize: '13px', cursor: 'pointer' }}>가입인사 게시판 글 작성 여부 필수 체크</label>
                  </div>
                </div>
              </div>

              {/* 디스코드 알림 설정 */}
              <div>
                <h4 style={{ color: 'var(--primary)', margin: '0 0 12px 0', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '6px' }}>디스코드 알림 및 모니터링 게시판</h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <label style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>디스코드 기본 Webhook URL (백업용)</label>
                    <input 
                      type="text" 
                      value={settings.discord.webhook_url || ''} 
                      onChange={e => setSettings({...settings, discord: {...settings.discord, webhook_url: e.target.value}})}
                      placeholder="https://discord.com/api/webhooks/..."
                    />
                  </div>
                  
                  {/* 개별 웹훅 주소 그리드 */}
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px' }}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                      <label style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>🚨 신고 알림 전용 Webhook URL</label>
                      <input 
                        type="text" 
                        value={settings.discord.report_webhook_url || ''} 
                        onChange={e => setSettings({...settings, discord: {...settings.discord, report_webhook_url: e.target.value}})}
                        placeholder="미설정 시 기본 웹훅 사용"
                      />
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                      <label style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>💡 건의 알림 전용 Webhook URL</label>
                      <input 
                        type="text" 
                        value={settings.discord.suggestion_webhook_url || ''} 
                        onChange={e => setSettings({...settings, discord: {...settings.discord, suggestion_webhook_url: e.target.value}})}
                        placeholder="미설정 시 기본 웹훅 사용"
                      />
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                      <label style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>⚙️ 작업 로그 전용 Webhook URL</label>
                      <input 
                        type="text" 
                        value={settings.discord.log_webhook_url || ''} 
                        onChange={e => setSettings({...settings, discord: {...settings.discord, log_webhook_url: e.target.value}})}
                        placeholder="미설정 시 기본 웹훅 사용"
                      />
                    </div>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                      <label style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>신고 게시판 이름</label>
                      <input 
                        type="text" 
                        value={settings.discord.report_board_name} 
                        onChange={e => setSettings({...settings, discord: {...settings.discord, report_board_name: e.target.value}})}
                      />
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                      <label style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>건의 사항 게시판 이름</label>
                      <input 
                        type="text" 
                        value={settings.discord.suggestion_board_name} 
                        onChange={e => setSettings({...settings, discord: {...settings.discord, suggestion_board_name: e.target.value}})}
                      />
                    </div>
                  </div>
                </div>
              </div>

              {/* 뉴스 크롤링 및 요약 */}
              <div>
                <h4 style={{ color: 'var(--primary)', margin: '0 0 12px 0', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '6px' }}>뉴스 자동 발행 & AI 요약 설정</h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                  <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '16px' }}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                      <label style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>뉴스 수집 대상 URL (네이버 e스포츠 롤)</label>
                      <input 
                        type="text" 
                        value={settings.news.target_url} 
                        onChange={e => setSettings({...settings, news: {...settings.news, target_url: e.target.value}})}
                      />
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                      <label style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>작성 대상 카페 게시판 ID</label>
                      <input 
                        type="text" 
                        value={settings.news.publish_board_id} 
                        onChange={e => setSettings({...settings, news: {...settings.news, publish_board_id: e.target.value}})}
                        placeholder="예: 12"
                      />
                    </div>
                  </div>

                  {/* LCK 팀 키워드 태그 관리 */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <label style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>팀별 균등 분배용 LCK 팀 목록 (단어 입력 후 Enter)</label>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', background: 'rgba(0,0,0,0.2)', padding: '10px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)' }}>
                      {settings.news.teams.map((team, idx) => (
                        <span key={idx} className="badge" style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', background: 'var(--primary)', color: '#fff' }}>
                          {team}
                          <X size={12} style={{ cursor: 'pointer' }} onClick={() => {
                            const newTeams = settings.news.teams.filter((_, i) => i !== idx);
                            setSettings({...settings, news: {...settings.news, teams: newTeams}});
                          }} />
                        </span>
                      ))}
                      <input 
                        type="text" 
                        placeholder="추가..." 
                        value={teamInput}
                        onChange={e => setTeamInput(e.target.value)}
                        onKeyDown={e => {
                          if (e.key === 'Enter' && teamInput.trim()) {
                            e.preventDefault();
                            if (!settings.news.teams.includes(teamInput.trim())) {
                              setSettings({...settings, news: {...settings.news, teams: [...settings.news.teams, teamInput.trim()]}});
                            }
                            setTeamInput('');
                          }
                        }}
                        style={{ border: 'none', background: 'transparent', padding: '2px 6px', width: '80px', fontSize: '12px' }}
                      />
                    </div>
                  </div>

                  {/* 인터뷰 우선순위 키워드 */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <label style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>인터뷰 우선 감지 키워드 (단어 입력 후 Enter)</label>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', background: 'rgba(0,0,0,0.2)', padding: '10px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)' }}>
                      {settings.news.interview_keywords.map((kw, idx) => (
                        <span key={idx} className="badge" style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', background: 'var(--secondary)', color: '#fff' }}>
                          {kw}
                          <X size={12} style={{ cursor: 'pointer' }} onClick={() => {
                            const newKws = settings.news.interview_keywords.filter((_, i) => i !== idx);
                            setSettings({...settings, news: {...settings.news, interview_keywords: newKws}});
                          }} />
                        </span>
                      ))}
                      <input 
                        type="text" 
                        placeholder="추가..." 
                        value={keywordInput}
                        onChange={e => setKeywordInput(e.target.value)}
                        onKeyDown={e => {
                          if (e.key === 'Enter' && keywordInput.trim()) {
                            e.preventDefault();
                            if (!settings.news.interview_keywords.includes(keywordInput.trim())) {
                              setSettings({...settings, news: {...settings.news, interview_keywords: [...settings.news.interview_keywords, keywordInput.trim()]}});
                            }
                            setKeywordInput('');
                          }
                        }}
                        style={{ border: 'none', background: 'transparent', padding: '2px 6px', width: '80px', fontSize: '12px' }}
                      />
                    </div>
                  </div>

                  {/* OpenAI API Key 연동 설정 */}
                  <div style={{ 
                    border: '1px solid rgba(255,255,255,0.05)', 
                    borderRadius: '10px', 
                    padding: '16px',
                    background: 'rgba(0, 0, 0, 0.1)'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '14px' }}>
                      <input 
                        type="checkbox" 
                        id="useLlm" 
                        checked={settings.news.use_llm_summary} 
                        onChange={e => setSettings({...settings, news: {...settings.news, use_llm_summary: e.target.checked}})}
                        style={{ width: '18px', height: '18px', cursor: 'pointer' }}
                      />
                      <label htmlFor="useLlm" style={{ fontSize: '14px', fontWeight: 600, cursor: 'pointer' }}>GPT (OpenAI) 뉴스 지능형 요약 엔진 활성화</label>
                    </div>
                    {settings.news.use_llm_summary && (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                        <label style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>OpenAI API Key</label>
                        <input 
                          type="password" 
                          value={settings.news.openai_api_key} 
                          onChange={e => setSettings({...settings, news: {...settings.news, openai_api_key: e.target.value}})}
                          placeholder="sk-proj-..."
                          style={{ width: '100%' }}
                        />
                        <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>API Key가 올바르지 않거나 미등록 시 무료 텍스트 중요도 파싱 알고리즘으로 자동 전환(Fallback)됩니다.</span>
                      </div>
                    )}
                  </div>

                </div>
              </div>

            </div>

            {/* 하단 저장 버튼 */}
            <div style={{ marginTop: '32px', display: 'flex', justifyContent: 'flex-end' }}>
              <button type="submit" className="btn-primary" disabled={loading} style={{ padding: '12px 28px' }}>
                <Save size={16} /> 설정 변경 사항 저장
              </button>
            </div>
          </form>
        )}

        {/* ==================== 3. 로그 및 아카이브 탭 ==================== */}
        {activeTab === 'logs' && (
          <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '20px' }}>
            
            {/* 왼쪽: 전체 시스템 로그 목록 */}
            <div className="glass-panel" style={{ padding: '24px' }}>
              <h3 className="gradient-text" style={{ margin: '0 0 16px 0', fontSize: '18px', fontWeight: 600 }}>전체 에이전트 이력 로그</h3>
              <div style={{ overflowY: 'auto', maxHeight: '600px' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', textAlign: 'left', color: 'var(--text-muted)' }}>
                      <th style={{ padding: '10px' }}>시간</th>
                      <th style={{ padding: '10px' }}>분류</th>
                      <th style={{ padding: '10px' }}>상태</th>
                      <th style={{ padding: '10px' }}>세부 동작 메시지</th>
                    </tr>
                  </thead>
                  <tbody>
                    {logs.map((log) => (
                      <tr key={log.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                        <td style={{ padding: '10px', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>{log.created_at}</td>
                        <td style={{ padding: '10px' }}>
                          <span className="badge" style={{ background: 'rgba(255,255,255,0.05)', color: '#fff', border: '1px solid rgba(255,255,255,0.1)' }}>{log.action_type}</span>
                        </td>
                        <td style={{ padding: '10px' }}>
                          <span className={`badge ${log.status === 'SUCCESS' ? 'badge-success' : 'badge-danger'}`}>{log.status}</span>
                        </td>
                        <td style={{ padding: '10px', color: 'var(--text-secondary)' }}>{log.message}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* 오른쪽: 뉴스 기사 아카이브 보관소 */}
            <div className="glass-panel" style={{ padding: '24px' }}>
              <h3 className="gradient-text" style={{ margin: '0 0 16px 0', fontSize: '18px', fontWeight: 600 }}>뉴스 기사 로컬 원문 보관소 (이미지 포함)</h3>
              <p style={{ fontSize: '12px', color: 'var(--text-muted)', margin: '-10px 0 20px 0' }}>수집 완료되어 로컬 스토리지에 영구 보관 중인 뉴스 아카이브 리스트입니다. 클릭 시 원문 뷰어로 조회할 수 있습니다.</p>
              
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', overflowY: 'auto', maxHeight: '550px' }}>
                {archives.map((arch) => (
                  <div 
                    key={arch.id} 
                    onClick={() => handleOpenArchive(arch)}
                    className="glass-panel" 
                    style={{ 
                      padding: '16px', 
                      cursor: 'pointer', 
                      background: 'rgba(255,255,255,0.02)',
                      border: '1px solid rgba(255,255,255,0.04)',
                      transition: 'var(--transition-fast)'
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.borderColor = 'rgba(255,255,255,0.1)'}
                    onMouseLeave={(e) => e.currentTarget.style.borderColor = 'rgba(255,255,255,0.04)'}
                  >
                    <h4 style={{ margin: '0 0 8px 0', fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)' }}>{arch.title}</h4>
                    <p style={{ 
                      margin: '0 0 12px 0', 
                      fontSize: '12px', 
                      color: 'var(--text-secondary)',
                      display: '-webkit-box',
                      WebkitLineClamp: 2,
                      WebkitBoxOrient: 'vertical',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis'
                    }}>
                      {arch.summary}
                    </p>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '11px', color: 'var(--text-muted)' }}>
                      <span>보관일시: {arch.published_at}</span>
                      <span style={{ color: 'var(--primary)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                        원문 보기 <ArrowRight size={10} />
                      </span>
                    </div>
                  </div>
                ))}
                {archives.length === 0 && (
                  <p style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '40px 0' }}>보관된 뉴스 기사가 없습니다.</p>
                )}
              </div>
            </div>

          </div>
        )}

      </main>

      {/* ==================== 뉴스 아카이브 본문 보기 모달 ==================== */}
      {selectedArchive && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0,0,0,0.85)',
          zIndex: 1000,
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          padding: '40px'
        }}>
          <div className="glass-panel" style={{
            width: '100%',
            maxWidth: '800px',
            maxHeight: '90vh',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
            background: '#0d0f1a',
            borderColor: 'rgba(255,255,255,0.15)'
          }}>
            {/* 모달 헤더 */}
            <div style={{ 
              padding: '20px 24px', 
              borderBottom: '1px solid rgba(255,255,255,0.08)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}>
              <div>
                <span className="badge badge-success" style={{ marginBottom: '6px', display: 'inline-block' }}>Local Archived Content</span>
                <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 600 }}>{selectedArchive.title}</h3>
              </div>
              <button 
                onClick={() => {
                  setSelectedArchive(null);
                  setArchiveHtml('');
                }} 
                className="btn-secondary" 
                style={{ padding: '6px', borderRadius: '50%' }}
              >
                <X size={18} />
              </button>
            </div>
            
            {/* 모달 본문 (HTML 렌더러) */}
            <div className="custom-article-body" style={{ 
              padding: '24px', 
              overflowY: 'auto', 
              flex: 1, 
              fontSize: '14px', 
              lineHeight: '1.7',
              color: 'var(--text-secondary)'
            }}>
              {/* 이미지와 글 서빙 */}
              <div 
                dangerouslySetInnerHTML={{ __html: archiveHtml }} 
                style={{
                  // 모달 이미지 반응형 크기 설정
                  maxWidth: '100%'
                }}
              />
            </div>
            
            {/* 모달 푸터 */}
            <div style={{ 
              padding: '16px 24px', 
              borderTop: '1px solid rgba(255,255,255,0.08)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              background: 'rgba(0,0,0,0.2)'
            }}>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                수집 일시: {selectedArchive.published_at}
              </span>
              <a 
                href={selectedArchive.source_url} 
                target="_blank" 
                rel="noreferrer" 
                className="btn-secondary" 
                style={{ padding: '6px 14px', fontSize: '12px' }}
              >
                네이버 원문 바로가기 <ExternalLink size={12} />
              </a>
            </div>
          </div>
        </div>
      )}
      
      {/* 이미지 렌더링 스타일 보완을 위한 style 태그 */}
      <style>{`
        .custom-article-body img {
          max-width: 100%;
          height: auto;
          border-radius: 8px;
          margin: 16px 0;
          border: 1px solid rgba(255,255,255,0.05);
        }
      `}</style>
    </div>
  );
}

export default App;
