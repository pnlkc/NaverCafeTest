/**
 * 대시보드 공통 유틸리티 함수 및 상수 모음
 * - 카테고리 매핑, 상태 뱃지 변환, 시간 포맷팅
 */

// 한글 카테고리 매핑 상수
export const CATEGORY_MAP = {
  ALL: '전체 보기',
  NEWS_SCRAPING: '뉴스 수집/발행',
  JOIN_APPROVE: '가입 승인 관리',
  LEVEL_UP: '회원 등업 관리',
  BOARD_MONITOR: '게시판 감시 기록',
  SCHEDULER: '자동 스케줄러',
  SYSTEM: '시스템 제어'
};

// 작업 유형 → 한글 라벨 + 뱃지 색상
export function getFriendlyCategory(type) {
  if (!type) return { label: '일반', color: 'badge-info' };
  if (type.includes('NEWS_PUBLISH') || type.includes('NEWS_SCRAPING')) {
    return { label: '뉴스 수집/발행', color: 'badge-info' };
  }
  if (type.includes('JOIN_APPROVE')) return { label: '가입 승인 관리', color: 'badge-success' };
  if (type.includes('LEVEL_UP')) return { label: '회원 등업 관리', color: 'badge-success' };
  if (type.includes('BOARD_MONITOR')) return { label: '게시판 감시', color: 'badge-warning' };
  if (type.includes('SCHEDULER')) return { label: '자동 스케줄러', color: 'badge-info' };
  return { label: type, color: 'badge-info' };
}

// 상태 코드 → 한글 라벨 + 뱃지 색상
export function getFriendlyStatus(status) {
  if (status === 'SUCCESS') return { label: '성공', badge: 'badge-success' };
  if (status === 'WARNING') return { label: '주의', badge: 'badge-warning' };
  if (status === 'FAILED' || status === 'ERROR') return { label: '오류', badge: 'badge-danger' };
  return { label: '안내', badge: 'badge-info' };
}

// 남은 초 → 사람이 읽기 쉬운 한글 표현
export function formatRemainingTime(sec) {
  if (sec == null || isNaN(sec)) return '확인 중...';
  if (sec <= 0) return '곧 실행 예정';
  if (sec < 60) return `${sec}초 후`;
  const min = Math.floor(sec / 60);
  const remSec = sec % 60;
  if (min < 60) return `${min}분 ${remSec}초 후`;
  const hr = Math.floor(min / 60);
  const remMin = min % 60;
  return `${hr}시간 ${remMin}분 후`;
}

// 주기(초) → 한글 주기 문구
export function formatInterval(sec) {
  if (sec == null || isNaN(sec)) return '주기 설정 확인 중';
  if (sec < 60) return `주기: ${sec}초마다`;
  const min = Math.floor(sec / 60);
  if (min < 60) return `주기: ${min}분마다`;
  const hr = Math.floor(min / 60);
  return `주기: ${hr}시간마다`;
}

// e스포츠 팀명 정규화 유틸리티 (이명 및 티커 통일)
export function getNormalizedTeamName(rawTeam) {
  if (!rawTeam) return '일반';
  const t = rawTeam.trim().toUpperCase();
  if (['DK', '디플러스', '디플러스기아', 'DPLUS', '담원', 'DWG'].includes(t) || t.includes('디플러스') || t.includes('담원')) return 'DK';
  if (['GEN.G', 'GENG', 'GEN', '젠지'].includes(t) || t.includes('젠지')) return 'GEN.G';
  if (['HLE', '한화', '한화생명'].includes(t) || t.includes('한화')) return 'HLE';
  if (['KT', '롤스터', '케이티'].includes(t) || t.includes('롤스터')) return 'KT';
  if (['FOX', '피어엑스', 'BNK', 'FEARX'].includes(t) || t.includes('피어엑스')) return 'FOX';
  if (['KDF', '광동', 'KWANGDONG', '프릭스'].includes(t) || t.includes('광동')) return 'KDF';
  if (['DRX', '디알엑스'].includes(t) || t.includes('DRX')) return 'DRX';
  if (['NS', '농심', 'NONGSHIM'].includes(t) || t.includes('농심')) return 'NS';
  if (['BRO', '브리온', 'BRION'].includes(t) || t.includes('브리온')) return 'BRO';
  if (['T1', 'SKT', '티원'].includes(t) || t.includes('T1')) return 'T1';
  return rawTeam;
}
