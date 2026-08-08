import React, { useState, useEffect } from 'react';
import {
  Settings,
  Activity,
  FileText,
  RefreshCw,
  UserCheck,
  Bell,
  BookOpen,
  ExternalLink,
  Save,
  X,
  Shield,
  Users,
  AlertTriangle,
  Clock,
  Sparkles,
  Zap,
  ChevronRight,
  ChevronLeft,
  Eye
} from 'lucide-react';

// 공통 유틸리티
import { CATEGORY_MAP, getFriendlyCategory, getFriendlyStatus, formatRemainingTime, formatInterval, getNormalizedTeamName } from './utils';

// 공통 컴포넌트
import SidebarNavButton from './components/SidebarNavButton';
import PageHeader from './components/PageHeader';
import MetricCard from './components/MetricCard';
import SearchInput from './components/SearchInput';
import FilterChipGroup from './components/FilterChipGroup';
import DataTable from './components/DataTable';
import LogItem from './components/LogItem';
import QuickActionCard from './components/QuickActionCard';
import ToastBar from './components/ToastBar';

const API_BASE = window.location.hostname === 'localhost' ? 'http://localhost:8000' : '';

function App() {

  const getInitialTab = () => {
    const hash = window.location.hash.replace('#', '');
    if (['dashboard', 'members', 'alerts', 'archives', 'logs', 'settings'].includes(hash)) {
      return hash;
    }
    return 'dashboard';
  };

  const [activeTab, setActiveTab] = useState(getInitialTab);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [settings, setSettings] = useState(null);
  const [sessionStatus, setSessionStatus] = useState({ logged_in: false, message: '연동 상태 확인 중...' });
  const [logs, setLogs] = useState([]);
  const [archives, setArchives] = useState([]);
  const [memberActions, setMemberActions] = useState([]);
  const [boardAlerts, setBoardAlerts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [actionStatus, setActionStatus] = useState(null);
  const [logFilter, setLogFilter] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  
  // 오늘 처리된 내역만 보기 필터 상태 (기본값: true = 오늘 내역만 보기)
  const [todayOnly, setTodayOnly] = useState(true);

  // 회원 가입 / 등업 전용 서브 필터 및 검색 상태
  const [memberSubFilter, setMemberSubFilter] = useState('ALL');
  const [memberSearchQuery, setMemberSearchQuery] = useState('');

  // 신고 / 건의 전용 서브 필터 및 검색 상태
  const [alertSubFilter, setAlertSubFilter] = useState('ALL');
  const [alertSearchQuery, setAlertSearchQuery] = useState('');

  // 아카이브 미리보기 모달 상태
  const [selectedArchive, setSelectedArchive] = useState(null);
  const [archiveHtml, setArchiveHtml] = useState('');
  const [archiveCategory, setArchiveCategory] = useState('ALL');

  // 스케줄러 다음 실행 시각 상태
  const [schedulerStatus, setSchedulerStatus] = useState(null);

  const renderTaskStatusBadge = (taskKey, colorClass = 'text-slate-400') => {
    const task = schedulerStatus?.tasks?.[taskKey];
    const isGlobalRunning = schedulerStatus?.is_running;
    const isActive = isGlobalRunning && (task?.is_active ?? true);

    if (!isActive) {
      return (
        <span className="text-rose-400 font-bold flex items-center gap-1 bg-rose-500/10 px-2 py-0.5 rounded border border-rose-500/20" title="현재 해당 자동 스케줄러 기능이 정지된 상태입니다.">
          <span className="w-1.5 h-1.5 rounded-full bg-rose-500 animate-ping"></span>
          🔴 스케줄러 정지됨
        </span>
      );
    }

    return (
      <span className={`${colorClass} font-medium flex items-center gap-1`}>
        <Clock className="w-3 h-3" />
        {formatRemainingTime(task?.remaining_seconds)}
      </span>
    );
  };

  // ─── API 호출 함수 ───────────────────────────────

  const fetchSchedulerStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/scheduler/status`);
      if (res.ok) {
        const data = await res.json();
        setSchedulerStatus(data);
      }
    } catch (e) {
      console.error('스케줄러 다음 실행 정보 로드 실패:', e);
    }
  };

  // 대시보드 통계 메트릭 상태 (SQLite DB 집계값)
  const [stats, setStats] = useState({
    today_news_count: 0,
    total_news_count: 0,
    total_approve_count: 0,
    total_levelup_count: 0,
    total_alert_count: 0,
    today_report_count: 0,
    today_suggestion_count: 0
  });

  const fetchStats = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/stats`);
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch (e) {
      console.error('대시보드 통계 조회 실패:', e);
    }
  };

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
      const res = await fetch(`${API_BASE}/api/logs?limit=100&today_only=${todayOnly}`);
      const data = await res.json();
      setLogs(data.items || []);
    } catch (e) {
      console.error('Failed to fetch logs:', e);
    }
  };

  const fetchArchives = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/archives?limit=40`);
      const data = await res.json();
      setArchives(data.items || []);
    } catch (e) {
      console.error('아카이브 조회 실패:', e);
    }
  };

  const fetchMemberActions = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/member-actions?limit=100&today_only=${todayOnly}`);
      const data = await res.json();
      setMemberActions(data.items || []);
    } catch (e) {
      console.error('회원 이력 조회 실패:', e);
    }
  };

  const fetchBoardAlerts = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/board-alerts?limit=100&today_only=${todayOnly}`);
      const data = await res.json();
      setBoardAlerts(data.items || []);
    } catch (e) {
      console.error('게시판 감시 조회 실패:', e);
    }
  };

  // ─── 액션 핸들러 ───────────────────────────────

  const handleSaveSettings = async (e) => {
    if (e) e.preventDefault();
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
      });
      if (res.ok) {
        setActionStatus({ type: 'success', message: '설정이 성공적으로 저장되었습니다!' });
        fetchSettings();
      } else {
        setActionStatus({ type: 'error', message: '설정 저장 중 문제가 발생했습니다.' });
      }
    } catch (e) {
      setActionStatus({ type: 'error', message: `오류 발생: ${e.message}` });
    } finally {
      setLoading(false);
      setTimeout(() => setActionStatus(null), 4000);
    }
  };

  const handleRunTaskNow = async (taskType) => {
    setLoading(true);
    let endpoint = `/api/action/news-publish`;
    if (taskType === 'join_approve') endpoint = `/api/action/join-approve`;
    else if (taskType === 'level_up') endpoint = `/api/action/level-up`;

    try {
      const res = await fetch(`${API_BASE}${endpoint}`, { method: 'POST' });
      const data = await res.json();
      if (res.ok) {
        setActionStatus({ type: 'success', message: data.message || '수동 실행 요청이 완료되었습니다.' });
        fetchLogs();
      } else {
        setActionStatus({ type: 'error', message: data.message || '수동 실행 실패' });
      }
    } catch (e) {
      setActionStatus({ type: 'error', message: `오류 발생: ${e.message}` });
    } finally {
      setLoading(false);
      setTimeout(() => setActionStatus(null), 4000);
    }
  };

  const handleOpenArchiveModal = async (archive) => {
    setSelectedArchive(archive);
    try {
      const res = await fetch(`${API_BASE}/api/archives/${archive.id}`);
      const data = await res.json();
      setArchiveHtml(data.content_html || '<p style="color:#a0a5c1;">내용을 불러올 수 없습니다.</p>');
    } catch (e) {
      setArchiveHtml('<p style="color:#ff1744;">아카이브 내용을 로드하는 중 에러가 발생했습니다.</p>');
    }
  };

  const handleRetryPost = async (archiveId) => {
    setLoading(true);
    setActionStatus({ type: 'success', message: '네이버 카페에 게시글 작성을 시도하고 있습니다. 잠시만 기다려주세요...' });
    try {
      const res = await fetch(`${API_BASE}/api/archives/${archiveId}/retry-post`, {
        method: 'POST'
      });
      const data = await res.json();
      if (res.ok && data.status === 'SUCCESS') {
        setActionStatus({ type: 'success', message: data.message || '게시글이 성공적으로 작성되었습니다!' });
        fetchArchives();
        fetchLogs();
        fetchStats();
      } else {
        setActionStatus({ type: 'error', message: data.message || '게시글 작성에 실패했습니다.' });
      }
    } catch (e) {
      setActionStatus({ type: 'error', message: `오류 발생: ${e.message}` });
    } finally {
      setLoading(false);
      setTimeout(() => setActionStatus(null), 5000);
    }
  };

  // ─── useEffect 훅 ───────────────────────────────

  // 1초 단위 실시간 카운트다운 타이머
  useEffect(() => {
    const timer = setInterval(() => {
      setSchedulerStatus(prev => {
        if (!prev || !prev.tasks) return prev;
        const updatedTasks = {};
        for (const [key, task] of Object.entries(prev.tasks)) {
          if (task && typeof task.remaining_seconds === 'number') {
            updatedTasks[key] = {
              ...task,
              remaining_seconds: Math.max(0, task.remaining_seconds - 1)
            };
          } else {
            updatedTasks[key] = task;
          }
        }
        return { ...prev, tasks: updatedTasks };
      });
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  // URL 해시 딥링크 자동 탭 전환
  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash.replace('#', '');
      if (['dashboard', 'members', 'alerts', 'archives', 'logs', 'settings'].includes(hash)) {
        setActiveTab(hash);
      }
    };
    handleHashChange();
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  // activeTab 변경 시 주소창 URL Hash 동기화 (각 관리자 페이지 주소 변경 보장)
  useEffect(() => {
    if (activeTab && window.location.hash.replace('#', '') !== activeTab) {
      window.location.hash = activeTab;
    }
  }, [activeTab]);

  // 초기 데이터 로드 + 폴링
  useEffect(() => {
    fetchSettings();
    fetchSessionStatus();
    fetchLogs();
    fetchArchives();
    fetchMemberActions();
    fetchBoardAlerts();
    fetchSchedulerStatus();
    fetchStats();

    const interval = setInterval(() => {
      fetchSessionStatus();
      fetchSchedulerStatus();
      fetchStats();
      if (activeTab === 'dashboard') {
        fetchLogs();
        fetchMemberActions();
        fetchBoardAlerts();
      }
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  // 탭 전환 및 오늘 필터 변경 시 데이터 갱신
  useEffect(() => {
    if (activeTab === 'logs' || activeTab === 'dashboard') {
      fetchLogs();
    }
    if (activeTab === 'archives' || activeTab === 'dashboard') {
      fetchArchives();
    }
    if (activeTab === 'members') {
      fetchMemberActions();
    }
    if (activeTab === 'alerts') {
      fetchBoardAlerts();
    }
  }, [activeTab, todayOnly]);

  // ─── 파생 데이터 ───────────────────────────────

  const todayNewsCount = stats.today_news_count;
  const totalApproveCount = stats.total_approve_count;
  const totalLevelupCount = stats.total_levelup_count;
  const todayReportCount = stats.today_report_count || 0;
  const todaySuggestionCount = stats.today_suggestion_count || 0;


  // 로그 필터링
  const filteredLogs = logs.filter(log => {
    const matchesCategory = logFilter === 'ALL' || 
      (logFilter === 'NEWS_SCRAPING' 
        ? (log.action_type.includes('NEWS_SCRAPING') || log.action_type.includes('NEWS_PUBLISH'))
        : log.action_type.includes(logFilter));
    const matchesSearch = !searchQuery || 
      log.message.toLowerCase().includes(searchQuery.toLowerCase()) ||
      log.action_type.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  // ─── 사이드바 내비게이션 데이터 ───────────────────

  const sidebarItems = [
    {
      key: 'dashboard',
      icon: Activity,
      label: '종합 관리 현황',
      isActive: activeTab === 'dashboard',
      onClick: () => setActiveTab('dashboard')
    },
    {
      key: 'join_approve',
      icon: UserCheck,
      label: '가입 승인 관리',
      isActive: activeTab === 'members' && memberSubFilter === 'JOIN_APPROVE',
      onClick: () => { setActiveTab('members'); setMemberSubFilter('JOIN_APPROVE'); },
      badge: totalApproveCount > 0 ? { value: totalApproveCount, bgColor: 'bg-emerald-500/20', textColor: 'text-emerald-300', borderColor: 'border-emerald-500/30' } : null,
      badgeDotColor: 'bg-emerald-400'
    },
    {
      key: 'level_up',
      icon: Sparkles,
      label: '회원 등업 관리',
      isActive: activeTab === 'members' && memberSubFilter === 'LEVEL_UP',
      onClick: () => { setActiveTab('members'); setMemberSubFilter('LEVEL_UP'); },
      badge: totalLevelupCount > 0 ? { value: totalLevelupCount, bgColor: 'bg-indigo-500/20', textColor: 'text-indigo-300', borderColor: 'border-indigo-500/30' } : null,
      badgeDotColor: 'bg-indigo-400'
    },
    {
      key: 'report',
      icon: AlertTriangle,
      label: '게시판 신고 관리',
      isActive: activeTab === 'alerts' && alertSubFilter === 'REPORT',
      onClick: () => { setActiveTab('alerts'); setAlertSubFilter('REPORT'); },
      badge: todayReportCount > 0 ? { value: todayReportCount, bgColor: 'bg-rose-500/20', textColor: 'text-rose-300', borderColor: 'border-rose-500/30' } : null,
      badgeDotColor: 'bg-rose-500'
    },
    {
      key: 'suggestion',
      icon: Bell,
      label: '게시판 건의 관리',
      isActive: activeTab === 'alerts' && alertSubFilter === 'SUGGESTION',
      onClick: () => { setActiveTab('alerts'); setAlertSubFilter('SUGGESTION'); },
      badge: todaySuggestionCount > 0 ? { value: todaySuggestionCount, bgColor: 'bg-amber-500/20', textColor: 'text-amber-300', borderColor: 'border-amber-500/30' } : null,
      badgeDotColor: 'bg-amber-500'
    },
    {
      key: 'archives',
      icon: FileText,
      label: '뉴스 발행 보관함',
      isActive: activeTab === 'archives',
      onClick: () => setActiveTab('archives')
    },
    {
      key: 'logs',
      icon: BookOpen,
      label: '실시간 작업 이력',
      isActive: activeTab === 'logs',
      onClick: () => setActiveTab('logs')
    },
    {
      key: 'settings',
      icon: Settings,
      label: '자동화 환경 설정',
      isActive: activeTab === 'settings',
      onClick: () => setActiveTab('settings')
    }
  ];

  // ─── 대시보드 메트릭 카드 데이터 ───────────────────

  const metricCards = [
    {
      title: '오늘 발행 뉴스',
      value: todayNewsCount,
      unit: '건',
      icon: FileText,
      colorScheme: {
        hover: 'hover:border-purple-500/60',
        text: 'group-hover:text-purple-300',
        iconBg: 'bg-purple-500/10',
        iconText: 'text-purple-400',
        iconBorder: 'border-purple-500/20',
        iconBgHover: 'group-hover:bg-purple-500/20',
        intervalText: 'text-purple-300'
      },
      intervalLabel: formatInterval(settings?.intervals?.news_publish),
      schedulerBadge: renderTaskStatusBadge('news_publish'),
      onClick: () => setActiveTab('archives')
    },
    {
      title: '오늘 가입 승인',
      value: totalApproveCount,
      unit: '명',
      icon: UserCheck,
      colorScheme: {
        hover: 'hover:border-emerald-500/60',
        text: 'group-hover:text-emerald-300',
        iconBg: 'bg-emerald-500/10',
        iconText: 'text-emerald-400',
        iconBorder: 'border-emerald-500/20',
        iconBgHover: 'group-hover:bg-emerald-500/20',
        intervalText: 'text-emerald-300'
      },
      intervalLabel: formatInterval(settings?.intervals?.join_approve),
      schedulerBadge: renderTaskStatusBadge('join_approve'),
      onClick: () => { setActiveTab('members'); setMemberSubFilter('JOIN_APPROVE'); }
    },
    {
      title: '오늘 회원 등업',
      value: totalLevelupCount,
      unit: '명',
      icon: Sparkles,
      colorScheme: {
        hover: 'hover:border-indigo-500/60',
        text: 'group-hover:text-indigo-300',
        iconBg: 'bg-indigo-500/10',
        iconText: 'text-indigo-400',
        iconBorder: 'border-indigo-500/20',
        iconBgHover: 'group-hover:bg-indigo-500/20',
        intervalText: 'text-indigo-300'
      },
      intervalLabel: formatInterval(settings?.intervals?.level_up),
      schedulerBadge: renderTaskStatusBadge('level_up'),
      onClick: () => { setActiveTab('members'); setMemberSubFilter('LEVEL_UP'); }
    },
    {
      title: '🚨 오늘 신고 알림',
      value: todayReportCount,
      unit: '건',
      icon: Bell,
      colorScheme: {
        hover: 'hover:border-rose-500/60',
        text: 'group-hover:text-rose-300',
        iconBg: 'bg-rose-500/10',
        iconText: 'text-rose-400',
        iconBorder: 'border-rose-500/20',
        iconBgHover: 'group-hover:bg-rose-500/20',
        intervalText: 'text-rose-300'
      },
      intervalLabel: formatInterval(settings?.intervals?.report_alert),
      schedulerBadge: renderTaskStatusBadge('board_monitor'),
      onClick: () => { setActiveTab('alerts'); setAlertSubFilter('REPORT'); }
    },
    {
      title: '💡 오늘 건의 알림',
      value: todaySuggestionCount,
      unit: '건',
      icon: Bell,
      colorScheme: {
        hover: 'hover:border-amber-500/60',
        text: 'group-hover:text-amber-300',
        iconBg: 'bg-amber-500/10',
        iconText: 'text-amber-400',
        iconBorder: 'border-amber-500/20',
        iconBgHover: 'group-hover:bg-amber-500/20',
        intervalText: 'text-amber-300'
      },
      intervalLabel: formatInterval(settings?.intervals?.report_alert),
      schedulerBadge: renderTaskStatusBadge('board_monitor'),
      onClick: () => { setActiveTab('alerts'); setAlertSubFilter('SUGGESTION'); }
    }
  ];

  // ─── 퀵 액션 데이터 ───────────────────────────────

  const quickActions = [
    {
      title: '👥 가입 신청 즉시 승인',
      description: '신규 가입 대기 회원들의 닉네임 규칙을 검사하여 자동 승인합니다.',
      colorScheme: 'emerald',
      onClick: () => handleRunTaskNow('join_approve')
    },
    {
      title: '⭐ 회원 조건 등업 체크',
      description: '전체 회원 활동 내역을 조회하여 조건 충족 시 바로 등업시킵니다.',
      colorScheme: 'indigo',
      onClick: () => handleRunTaskNow('level_up')
    },
    {
      title: '🚀 뉴스 수집 & AI 요약 발행',
      description: '최신 e스포츠 기사를 수집하고 AI 요약본으로 카페에 즉시 등록합니다.',
      colorScheme: 'purple',
      onClick: () => handleRunTaskNow('news_publish')
    }
  ];

  // ─── 회원 탭 필터 칩 데이터 ───────────────────────

  const memberFilterChips = [
    { key: 'ALL', label: '전체 내역', count: memberActions.length, activeColor: 'bg-indigo-600 shadow-indigo-600/30', countBg: 'bg-slate-800', countText: 'text-slate-300' },
    { key: 'JOIN_APPROVE', label: '👥 가입 승인만 보기', count: memberActions.filter(a => a.action_type?.includes('JOIN_APPROVE')).length, activeColor: 'bg-emerald-600 shadow-emerald-600/30', countBg: 'bg-emerald-950', countText: 'text-emerald-300' },
    { key: 'LEVEL_UP', label: '⭐ 자동 등업만 보기', count: memberActions.filter(a => a.action_type?.includes('LEVEL_UP')).length, activeColor: 'bg-indigo-600 shadow-indigo-600/30', countBg: 'bg-indigo-950', countText: 'text-indigo-300' }
  ];

  // ─── 신고/건의 탭 필터 칩 데이터 ─────────────────

  const alertFilterChips = [
    { key: 'ALL', label: '전체 게시글', count: boardAlerts.length, activeColor: 'bg-amber-600 shadow-amber-600/30', countBg: 'bg-slate-800', countText: 'text-slate-300' },
    { key: 'REPORT', label: '🚨 신고 게시판만 보기', count: boardAlerts.filter(a => a.board_type === 'REPORT').length, activeColor: 'bg-rose-600 shadow-rose-600/30', countBg: 'bg-rose-950', countText: 'text-rose-300' },
    { key: 'SUGGESTION', label: '💡 건의 사항만 보기', count: boardAlerts.filter(a => a.board_type === 'SUGGESTION').length, activeColor: 'bg-amber-600 shadow-amber-600/30', countBg: 'bg-amber-950', countText: 'text-amber-300' }
  ];

  // ─── 뉴스 기사 보관함 탭 필터 칩 데이터 ───────────

  const archiveTeamList = ['ALL', 'T1', 'GEN.G', 'HLE', 'DK', 'KT', 'FOX', 'KDF', 'DRX', 'NS', 'BRO', '일반'];
  
  // 기사 다중 팀 태그 매칭 헬퍼 함수
  const isTeamMatch = (itemTeam, cat) => {
    if (cat === 'ALL') return true;
    if (!itemTeam) return cat === '일반';
    const teams = itemTeam.split(',').map(t => getNormalizedTeamName(t.trim()).toUpperCase());
    return teams.includes(cat.toUpperCase());
  };

  const archiveFilterChips = archiveTeamList
    .map(cat => {
      const count = cat === 'ALL'
        ? archives.length
        : archives.filter(a => isTeamMatch(a.team, cat)).length;
      return {
        key: cat,
        label: cat === 'ALL' ? '🌐 전체 보기' : cat,
        count: count
      };
    })
    .filter(chip => chip.key === 'ALL' || chip.count > 0)
    .sort((a, b) => {
      if (a.key === 'ALL') return -1;
      if (b.key === 'ALL') return 1;
      return b.count - a.count;
    });

  const filteredArchives = archives.filter(item => isTeamMatch(item.team, archiveCategory));

  // ─── 시스템 이력 탭 필터 칩 데이터 ───────────────

  const logFilterChips = Object.entries(CATEGORY_MAP).map(([key, label]) => ({
    key,
    label
  }));

  // ─── 필터링된 데이터 ───────────────────────────────

  const filteredMembers = memberActions.filter(item => {
    if (memberSubFilter === 'JOIN_APPROVE' && !item.action_type?.includes('JOIN_APPROVE')) return false;
    if (memberSubFilter === 'LEVEL_UP' && !item.action_type?.includes('LEVEL_UP')) return false;
    if (memberSearchQuery) {
      const q = memberSearchQuery.toLowerCase();
      return (
        item.message?.toLowerCase().includes(q) ||
        item.action_type?.toLowerCase().includes(q) ||
        item.created_at?.toLowerCase().includes(q)
      );
    }
    return true;
  });

  const filteredAlerts = boardAlerts.filter(alert => {
    if (alertSubFilter === 'REPORT' && alert.board_type !== 'REPORT') return false;
    if (alertSubFilter === 'SUGGESTION' && alert.board_type !== 'SUGGESTION') return false;
    if (alertSearchQuery) {
      const q = alertSearchQuery.toLowerCase();
      return (
        alert.title?.toLowerCase().includes(q) ||
        alert.writer?.toLowerCase().includes(q) ||
        alert.created_at?.toLowerCase().includes(q)
      );
    }
    return true;
  });

  // ─── 테이블 컬럼 정의 ───────────────────────────────

  const memberColumns = [
    { key: 'time', label: '처리 시간' },
    { key: 'type', label: '작업 구분' },
    { key: 'detail', label: '대상 회원 / 상세 내용' },
    { key: 'status', label: '상태' }
  ];

  const alertColumns = [
    { key: 'time', label: '감지 시간' },
    { key: 'type', label: '게시판 유형' },
    { key: 'title', label: '게시글 제목' },
    { key: 'writer', label: '작성자' },
    { key: 'link', label: '바로가기' }
  ];

  // ─── 렌더링 ───────────────────────────────

  return (
    <div className="flex h-screen overflow-hidden text-gray-100 bg-slate-950 font-sans">
      {/* 1. 사이드바 메인 내비게이션 */}
      <aside className={`${isSidebarCollapsed ? 'w-20' : 'w-64'} bg-slate-900/90 backdrop-blur-xl border-r border-slate-800 flex flex-col justify-between z-20 transition-all duration-300`}>
        <div>
          {/* 브랜드 로고 & 타이틀 */}
          <div className={`p-4 border-b border-slate-800/80 flex items-center ${isSidebarCollapsed ? 'flex-col gap-3 justify-center' : 'justify-between'} transition-all duration-300`}>
            <div
              onClick={() => setActiveTab('dashboard')}
              className="flex items-center gap-3 cursor-pointer group"
              title="클릭 시 메인 대시보드로 이동합니다."
            >
              <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-fuchsia-600 flex items-center justify-center shadow-lg shadow-indigo-500/30 group-hover:scale-105 transition-transform shrink-0">
                <Sparkles className="w-5 h-5 text-white" />
              </div>
              {!isSidebarCollapsed && (
                <div className="transition-opacity duration-300">
                  <h1 className="font-bold text-base leading-tight gradient-text group-hover:opacity-90 transition-opacity whitespace-nowrap">네이버 카페 매니저</h1>
                  <p className="text-[10px] text-indigo-300 font-medium whitespace-nowrap">통합 자동화 제어판</p>
                </div>
              )}
            </div>
            <button 
              onClick={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
              className={`p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition-colors shrink-0 ${isSidebarCollapsed ? 'w-full flex justify-center' : ''}`}
              title={isSidebarCollapsed ? "사이드바 펴기" : "사이드바 접기"}
            >
              {isSidebarCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
            </button>
          </div>

          {/* 내비게이션 메뉴 — 데이터 기반 렌더링 */}
          <nav className="p-4 space-y-1.5">
            {sidebarItems.map(item => (
              <SidebarNavButton
                key={item.key}
                icon={item.icon}
                label={item.label}
                isActive={item.isActive}
                isCollapsed={isSidebarCollapsed}
                onClick={item.onClick}
                badge={item.badge}
                badgeDotColor={item.badgeDotColor}
              />
            ))}
          </nav>
        </div>

        {/* 세션 로그인 상태 요약 카드 */}
        {isSidebarCollapsed ? (
          <div className="p-4 mb-4 flex justify-center" title={sessionStatus.message || (sessionStatus.logged_in ? '네이버 로그인 연결 완료 (자동화 활성)' : '네이버 로그인 필요')}>
            <div className={`w-3.5 h-3.5 rounded-full ${sessionStatus.expiry_warning ? 'bg-amber-400 animate-ping' : (sessionStatus.logged_in ? 'bg-emerald-400 animate-pulse' : 'bg-rose-500')} border border-slate-800`}></div>
          </div>
        ) : (
          <div className={`p-4 m-4 rounded-2xl bg-slate-850 border ${sessionStatus.expiry_warning ? 'border-amber-500/50 bg-amber-950/20' : 'border-slate-800/90'}`}>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2.5">
                <div className={`w-2.5 h-2.5 rounded-full ${sessionStatus.expiry_warning ? 'bg-amber-400 animate-ping' : (sessionStatus.logged_in ? 'bg-emerald-400 animate-pulse' : 'bg-rose-500')}`}></div>
                <span className="text-xs font-semibold text-slate-300 whitespace-nowrap">네이버 카페 연동</span>
              </div>
              {sessionStatus.expiry_warning && (
                <span className="text-[10px] font-bold bg-amber-500/20 text-amber-300 px-1.5 py-0.5 rounded border border-amber-500/30">만료 임박</span>
              )}
            </div>
            <p className="text-xs text-slate-400 font-normal leading-snug">
              {sessionStatus.message || (sessionStatus.logged_in ? '네이버 로그인 연결 완료 (자동화 활성)' : '네이버 로그인 필요 (세션 확인 필요)')}
            </p>
          </div>
        )}
      </aside>

      {/* 2. 메인 컨텐츠 영역 */}
      <main className="flex-1 flex flex-col overflow-y-auto bg-gradient-to-br from-slate-950 via-slate-900 to-indigo-950/40">
        {/* 상단 알림 바 */}
        <ToastBar status={actionStatus} />

        {/* ─── 대시보드 메인 페이지 ─── */}
        {activeTab === 'dashboard' && (
          <div className="p-8 space-y-8 max-w-7xl mx-auto w-full">
            {/* 상단 웰컴 헤더 */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-900/60 backdrop-blur-md p-6 rounded-2xl border border-slate-800">
              <div>
                <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                  👋 안녕하세요, 카페 관리자님!
                </h2>
                <p className="text-slate-400 text-sm mt-1">
                  네이버 카페 자동 승인, 조건 등업, 뉴스 수집 및 신고 게시판 감시 상태가 실시간으로 작동 중입니다.
                </p>
                {schedulerStatus && (
                  <div className="mt-2.5 flex items-center gap-2">
                    {schedulerStatus.is_running ? (
                      <span className="inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                        🟢 전체 스케줄러 라이브 가동 중
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20 animate-bounce">
                        <span className="w-2 h-2 rounded-full bg-rose-500"></span>
                        🔴 전체 스케줄러 엔진 정지됨
                      </span>
                    )}
                  </div>
                )}
              </div>

              <div className="flex items-center gap-4">
                <label className="flex items-center gap-2 text-xs text-slate-300 hover:text-white cursor-pointer select-none bg-slate-800/40 px-3 py-1.5 rounded-lg border border-slate-700/50 hover:border-slate-600/80 transition-all">
                  <input
                    type="checkbox"
                    checked={todayOnly}
                    onChange={(e) => setTodayOnly(e.target.checked)}
                    className="rounded border-slate-700 bg-slate-900 text-indigo-500 focus:ring-indigo-500 w-3.5 h-3.5"
                  />
                  <span>📅 오늘 내역만 보기</span>
                </label>
                <button
                  onClick={() => {
                    fetchLogs();
                    fetchMemberActions();
                    fetchBoardAlerts();
                    fetchStats();
                  }}
                  className="btn-secondary text-xs"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  새로고침
                </button>
              </div>
            </div>

            {/* 메트릭 카드 5종 — 데이터 기반 렌더링 */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
              {metricCards.map(card => (
                <MetricCard
                  key={card.title}
                  title={card.title}
                  value={card.value}
                  unit={card.unit}
                  icon={card.icon}
                  colorScheme={card.colorScheme}
                  intervalLabel={card.intervalLabel}
                  schedulerBadge={card.schedulerBadge}
                  onClick={card.onClick}
                />
              ))}
            </div>

            {/* 수동 다이렉트 실행 퀵 액션 카드 */}
            <div className="glass-panel p-6">
              <h3 className="text-base font-bold text-white mb-4 flex items-center gap-2">
                <Zap className="w-4 h-4 text-indigo-400" />
                원클릭 수동 실행 도구
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {quickActions.map(action => (
                  <QuickActionCard
                    key={action.title}
                    title={action.title}
                    description={action.description}
                    colorScheme={action.colorScheme}
                    onClick={action.onClick}
                    disabled={loading}
                  />
                ))}
              </div>
            </div>

            {/* 최근 처리 이력 간략 모니터 */}
            <div className="glass-panel p-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <Clock className="w-4 h-4 text-indigo-400" />
                  최근 작업 자동 처리 기록
                </h3>
                <div className="flex items-center gap-4">
                  <button onClick={() => setActiveTab('logs')} className="text-xs text-indigo-400 hover:underline">
                    전체 기록 보기 →
                  </button>
                </div>
              </div>

              <div className="space-y-2.5">
                {logs
                  .filter(log => {
                    const msg = log.message || '';
                    return !msg.includes('없습니다') && !msg.includes('건너뜁니다');
                  })
                  .slice(0, 6)
                  .map((log, idx) => (
                    <LogItem
                      key={idx}
                      actionType={log.action_type}
                      message={log.message}
                      status={log.status}
                      timestamp={log.created_at}
                      showFullTimestamp={false}
                    />
                  ))}
              </div>
            </div>
          </div>
        )}

        {/* ─── 👥 가입 및 등업 관리 탭 ─── */}
        {activeTab === 'members' && (
          <div className="p-8 space-y-6 max-w-7xl mx-auto w-full">
            <PageHeader
              title="👥 회원 가입 승인 및 등업 내역"
              description="자동 가입 승인 처리된 회원과 조건에 따라 등업 처리된 회원들의 기록입니다."
            >
              <SearchInput
                placeholder="회원 닉네임 / 내역 검색..."
                value={memberSearchQuery}
                onChange={(e) => setMemberSearchQuery(e.target.value)}
              />
            </PageHeader>

            <FilterChipGroup
              chips={memberFilterChips}
              activeKey={memberSubFilter}
              onSelect={setMemberSubFilter}
            />

            <DataTable
              columns={memberColumns}
              data={filteredMembers}
              emptyMessage="조건에 해당하는 회원 가입 및 등업 이력이 없습니다."
              renderRow={(item, idx) => {
                const cat = getFriendlyCategory(item.action_type);
                const st = getFriendlyStatus(item.status);
                return (
                  <tr key={idx} className="hover:bg-slate-900/40 transition-colors">
                    <td className="py-3.5 text-xs text-slate-400">{item.created_at}</td>
                    <td className="py-3.5">
                      <span className={`px-2.5 py-1 rounded-lg text-xs font-semibold ${cat.color}`}>
                        {cat.label}
                      </span>
                    </td>
                    <td className="py-3.5 text-slate-200">{item.message}</td>
                    <td className="py-3.5">
                      <span className={`badge ${st.badge}`}>{st.label}</span>
                    </td>
                  </tr>
                );
              }}
            />
          </div>
        )}

        {/* ─── 🔔 게시판 신고·건의 감시 탭 ─── */}
        {activeTab === 'alerts' && (
          <div className="p-8 space-y-6 max-w-7xl mx-auto w-full">
            <PageHeader
              title="🔔 신고 및 건의 게시판 모니터링"
              description="카페 신고 게시판과 건의 게시판에 새로 등록된 게시글을 실시간 감지하여 알립니다."
            >
              <SearchInput
                placeholder="제목 / 작성자 검색..."
                value={alertSearchQuery}
                onChange={(e) => setAlertSearchQuery(e.target.value)}
                focusColor="focus:border-amber-500"
              />
            </PageHeader>

            <FilterChipGroup
              chips={alertFilterChips}
              activeKey={alertSubFilter}
              onSelect={setAlertSubFilter}
            />

            <DataTable
              columns={alertColumns}
              data={filteredAlerts}
              emptyMessage="조건에 해당하는 게시판 감지 내역이 없습니다."
              renderRow={(alert, idx) => (
                <tr key={idx} className="hover:bg-slate-900/40 transition-colors">
                  <td className="py-3.5 text-xs text-slate-400">{alert.created_at || alert.checked_at}</td>
                  <td className="py-3.5">
                    <span className={`badge ${alert.board_type === 'REPORT' ? 'badge-danger' : 'badge-warning'}`}>
                      {alert.board_type === 'REPORT' ? '🚨 신고 게시판' : '💡 건의 게시판'}
                    </span>
                  </td>
                  <td className="py-3.5 font-medium text-slate-100">{alert.title}</td>
                  <td className="py-3.5 text-slate-300">{alert.writer || '익명'}</td>
                  <td className="py-3.5">
                    {alert.article_url ? (
                      <a
                        href={alert.article_url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 text-xs text-indigo-400 hover:underline"
                      >
                        카페 보기 <ExternalLink className="w-3 h-3" />
                      </a>
                    ) : (
                      <span className="text-xs text-slate-600">-</span>
                    )}
                  </td>
                </tr>
              )}
            />
          </div>
        )}

        {/* ─── 📰 자동 발행 뉴스 기사 보관함 탭 ─── */}
        {activeTab === 'archives' && (
          <div className="p-8 space-y-6 max-w-7xl mx-auto w-full">
            <PageHeader
              title="📰 자동 포스팅 뉴스 기사 보관함"
              description="수집되어 네이버 카페에 성공적으로 자동 발행된 e스포츠 기사 본문과 AI 요약 기록입니다."
            >
              <button
                onClick={() => handleRunTaskNow('news_publish')}
                disabled={loading}
                className="btn-primary text-xs shrink-0 self-start md:self-auto"
              >
                <Zap className="w-3.5 h-3.5" />
                지금 뉴스 바로 수집/발행
              </button>
            </PageHeader>

            {/* 팀 / 카테고리 필터 칩 바 (공통 FilterChipGroup 사용) */}
            <div className="border-b border-slate-800/80 pb-3 pt-1">
              <FilterChipGroup
                chips={archiveFilterChips}
                activeKey={archiveCategory}
                onSelect={setArchiveCategory}
              />
            </div>

            {filteredArchives.length === 0 ? (
              <div className="glass-panel p-12 text-center text-slate-400">
                <FileText className="w-10 h-10 mx-auto mb-3 text-slate-600 animate-bounce" />
                <p className="font-semibold text-slate-300">선택하신 카테고리의 수집된 기사가 없습니다.</p>
                <p className="text-xs text-slate-500 mt-1">상단의 '지금 뉴스 바로 수집/발행' 버튼을 눌러 최신 기사를 수집해보세요.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                {filteredArchives.map((item, idx) => (
                  <div key={idx} className="glass-panel p-5 flex flex-col justify-between hover:border-indigo-500/40 transition-all">
                    <div>
                      <div className="flex items-center justify-between gap-2 mb-2">
                        <div className="flex flex-wrap items-center gap-1.5">
                          {(item.team || '일반').split(',').map((t, tIdx) => (
                            <span key={tIdx} className="badge badge-purple">
                              {getNormalizedTeamName(t.trim())}
                            </span>
                          ))}
                        </div>
                        <span className="text-xs text-slate-500">{item.published_at?.split(' ')[0]}</span>
                      </div>
                      <h3 className="font-bold text-base text-slate-100 mb-2 leading-snug">{item.title}</h3>
                      <p className="text-xs text-slate-400 line-clamp-3 mb-4">{item.summary}</p>
                    </div>
                    
                    <div className="flex items-center justify-between pt-3 border-t border-slate-800/80 text-xs">
                      <button
                        onClick={() => handleOpenArchiveModal(item)}
                        className="inline-flex items-center gap-1.5 text-indigo-400 hover:text-indigo-300 font-medium"
                      >
                        <Eye className="w-3.5 h-3.5" /> 미리보기
                      </button>
                      {item.cafe_article_url ? (
                        <a
                          href={item.cafe_article_url}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1.5 text-emerald-400 hover:text-emerald-300 font-medium"
                        >
                          네이버 카페 글보기 <ExternalLink className="w-3.5 h-3.5" />
                        </a>
                      ) : (
                        <button
                          onClick={() => handleRetryPost(item.id)}
                          disabled={loading}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 text-xs font-semibold transition-all disabled:opacity-50"
                          title="네이버 카페에 게시글 작성을 다시 시도합니다"
                        >
                          <Zap className="w-3.5 h-3.5 text-amber-400" />
                          게시글 작성하기
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ─── 📋 실시간 작업 이력 탭 ─── */}
        {activeTab === 'logs' && (
          <div className="p-8 space-y-6 max-w-7xl mx-auto w-full">
            <PageHeader
              title="📋 실시간 시스템 처리 기록"
              description="카페 자동화 봇의 모든 동작 로그를 한글 카테고리로 필터링하여 검색할 수 있습니다."
            />

            {/* 필터 및 검색 컨트롤 */}
            <div className="glass-panel p-4 flex flex-col md:flex-row items-center justify-between gap-4">
              <div className="w-full md:w-auto overflow-x-auto">
                <FilterChipGroup
                  chips={logFilterChips}
                  activeKey={logFilter}
                  onSelect={setLogFilter}
                />
              </div>

              <div className="flex flex-wrap items-center gap-4">
                <SearchInput
                  placeholder="작업 내용 검색..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
            </div>

            {/* 로그 목록 */}
            <div className="glass-panel p-6">
              <div className="space-y-2">
                {filteredLogs.length === 0 ? (
                  <div className="py-12 text-center text-slate-500">
                    조건에 해당하는 작업 이력이 없습니다.
                  </div>
                ) : (
                  filteredLogs.map((log, idx) => (
                    <LogItem
                      key={idx}
                      actionType={log.action_type}
                      message={log.message}
                      status={log.status}
                      timestamp={log.created_at}
                      showFullTimestamp={true}
                    />
                  ))
                )}
              </div>
            </div>
          </div>
        )}

        {/* ─── ⚙️ 자동화 환경 설정 탭 ─── */}
        {activeTab === 'settings' && settings && (
          <div className="p-8 space-y-6 max-w-5xl mx-auto w-full">
            <PageHeader
              title="⚙️ 카페 자동화 세부 설정"
              description="네이버 카페 ID, 자동 등업 조건, 뉴스 수집 설정 및 스케줄 주기를 편리하게 설정할 수 있습니다."
            />

            <form onSubmit={handleSaveSettings} className="space-y-6">
              {/* 네이버 카페 기본 설정 */}
              <div className="glass-panel p-6 space-y-4">
                <h3 className="text-base font-bold text-indigo-300 border-b border-slate-800 pb-3">
                  📌 네이버 카페 기본 정보
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-slate-400 mb-1.5">
                      카페 클럽 ID (Club ID) <span className="text-emerald-400 font-bold">* 필수 (자동화 핵심 식별자)</span>
                    </label>
                    <input
                      type="text"
                      value={settings.cafe?.club_id || ''}
                      onChange={(e) => setSettings({
                        ...settings,
                        cafe: { ...settings.cafe, club_id: e.target.value }
                      })}
                      className="w-full"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-400 mb-1.5">
                      카페 메인 URL <span className="text-slate-500 font-normal">(선택 / 대시보드 바로가기 참조용)</span>
                    </label>
                    <input
                      type="text"
                      placeholder="https://cafe.naver.com/yourcafe"
                      value={settings.cafe?.cafe_url || ''}
                      onChange={(e) => setSettings({
                        ...settings,
                        cafe: { ...settings.cafe, cafe_url: e.target.value }
                      })}
                      className="w-full text-slate-400"
                    />
                  </div>
                </div>
              </div>

              {/* 스케줄 주기 설정 */}
              <div className="glass-panel p-6 space-y-4">
                <h3 className="text-base font-bold text-indigo-300 border-b border-slate-800 pb-3">
                  ⏱️ 자동화 주기 설정 (초 단위)
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-slate-400 mb-1.5">가입 승인 주기 (초)</label>
                    <input
                      type="number"
                      value={settings.intervals?.join_approve || 60}
                      onChange={(e) => setSettings({
                        ...settings,
                        intervals: { ...settings.intervals, join_approve: parseInt(e.target.value) || 60 }
                      })}
                      className="w-full text-xs"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-400 mb-1.5">회원 등업 주기 (초)</label>
                    <input
                      type="number"
                      value={settings.intervals?.level_up || 300}
                      onChange={(e) => setSettings({
                        ...settings,
                        intervals: { ...settings.intervals, level_up: parseInt(e.target.value) || 300 }
                      })}
                      className="w-full text-xs"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-400 mb-1.5">게시판 감시 주기 (초)</label>
                    <input
                      type="number"
                      value={settings.intervals?.report_alert || 60}
                      onChange={(e) => setSettings({
                        ...settings,
                        intervals: { ...settings.intervals, report_alert: parseInt(e.target.value) || 60 }
                      })}
                      className="w-full text-xs"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-400 mb-1.5">뉴스 발행 주기 (초)</label>
                    <input
                      type="number"
                      value={settings.intervals?.news_publish || 86400}
                      onChange={(e) => setSettings({
                        ...settings,
                        intervals: { ...settings.intervals, news_publish: parseInt(e.target.value) || 86400 }
                      })}
                      className="w-full text-xs"
                    />
                  </div>
                </div>
              </div>

              {/* 저장 버튼 */}
              <div className="flex justify-end">
                <button type="submit" disabled={loading} className="btn-primary">
                  <Save className="w-4 h-4" />
                  설정 내용 저장하기
                </button>
              </div>
            </form>
          </div>
        )}
      </main>

      {/* 미리보기 모달 */}
      {selectedArchive && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-md z-50 flex items-center justify-center p-4 sm:p-6 animate-fade-in">
          <div className="glass-panel w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden bg-slate-900/95 border-slate-700/80 shadow-2xl rounded-2xl">
            {/* 모달 헤더 */}
            <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between gap-4 bg-slate-950/60">
              <div className="flex items-center gap-3 min-w-0">
                <div className="flex flex-wrap items-center gap-1.5 shrink-0">
                  {(selectedArchive.team || '일반').split(',').map((t, tIdx) => (
                    <span key={tIdx} className="badge badge-purple">
                      {getNormalizedTeamName(t.trim())}
                    </span>
                  ))}
                </div>
                <h3 className="font-bold text-slate-100 text-base md:text-lg truncate" title={selectedArchive.title}>
                  {selectedArchive.title}
                </h3>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <span className="text-xs text-slate-400 hidden sm:inline-block">
                  {selectedArchive.published_at?.split(' ')[0]}
                </span>
                <button
                  onClick={() => setSelectedArchive(null)}
                  className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
                  title="미리보기 닫기"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* 모달 본문 (기사 상세 뷰어) */}
            <div className="p-6 md:p-8 overflow-y-auto flex-1 text-slate-200 text-sm naver-article-viewer custom-scrollbar">
              <div dangerouslySetInnerHTML={{ __html: archiveHtml }} />
            </div>

            {/* 모달 푸터 */}
            <div className="px-6 py-4 border-t border-slate-800/80 bg-slate-950/40 flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                {selectedArchive.source_url && (
                  <a
                    href={selectedArchive.source_url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 text-xs font-semibold transition-all"
                  >
                    <ExternalLink className="w-3.5 h-3.5" /> 원문 기사 보러가기
                  </a>
                )}
                {selectedArchive.cafe_article_url ? (
                  <a
                    href={selectedArchive.cafe_article_url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-xs font-semibold transition-all"
                  >
                    네이버 카페 글보기 <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                ) : (
                  <button
                    onClick={() => {
                      const archId = selectedArchive.id;
                      setSelectedArchive(null);
                      handleRetryPost(archId);
                    }}
                    disabled={loading}
                    className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 text-xs font-semibold transition-all disabled:opacity-50"
                  >
                    <Zap className="w-3.5 h-3.5 text-amber-400" />
                    게시글 작성하기
                  </button>
                )}
              </div>
              <button
                onClick={() => setSelectedArchive(null)}
                className="btn-secondary text-xs px-4 py-1.5"
              >
                닫기
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
