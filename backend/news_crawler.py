import os
import re
import httpx
import shutil
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

from typing import List, Dict, Any, Optional
from backend.config import load_settings, AppSettings
from backend.logger import log_event
from backend.database import NewsArchive, SessionLocal

# 아카이브 저장 폴더 설정
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIVE_DIR = os.path.join(BASE_DIR, "data", "archive")

# 글로벌 LoL e스포츠 팀 메타데이터 사전 (동적 수집용 메모리 보관소)
TEAM_METADATA = {}

# 로드 실패 혹은 테스트 시 사용될 2026시즌 실측 백업용 로컬 캐시 데이터
FALLBACK_TEAM_METADATA = {
    "T1": {
        "team_names": ["T1", "SKT", "SKT T1", "SK Telecom", "티원", "슼", "슼원"],
        "players": [
            {"id": "Zeus", "nickname": "제우스", "real_name": "최우제"},
            {"id": "Oner", "nickname": "오너", "real_name": "문현준"},
            {"id": "Faker", "nickname": "페이커", "real_name": "이상혁"},
            {"id": "Gumayusi", "nickname": "구마유시", "real_name": "이민형"},
            {"id": "Keria", "nickname": "케리아", "real_name": "류민석"}
        ],
        "coaches": [
            {"id": "Tom", "nickname": "톰", "real_name": "임재현"}
        ]
    },
    "젠지": {
        "team_names": ["젠지", "Gen.G", "GEN", "Gen.G Esports", "지오디", "젠", "젠에스"],
        "players": [
            {"id": "Kiin", "nickname": "기인", "real_name": "김기인"},
            {"id": "Canyon", "nickname": "캐니언", "real_name": "김건부"},
            {"id": "Chovy", "nickname": "쵸비", "real_name": "정지훈"},
            {"id": "Ruler", "nickname": "룰러", "real_name": "박재혁"},
            {"id": "Duro", "nickname": "듀로", "real_name": "주민규"}
        ],
        "coaches": [
            {"id": "Ryu", "nickname": "류", "real_name": "유상욱"},
            {"id": "Lyn", "nickname": "린", "real_name": "김다빈"},
            {"id": "Nova", "nickname": "노바", "real_name": "박찬호"}
        ]
    },
    "한화생명": {
        "team_names": ["한화생명", "HLE", "Hanwha Life", "한화", "한생", "오렌지 전차", "한화생명e스포츠"],
        "players": [
            {"id": "Doran", "nickname": "도란", "real_name": "최현준"},
            {"id": "Kanavi", "nickname": "카나비", "real_name": "서진혁"},
            {"id": "Zeka", "nickname": "제카", "real_name": "김건우"},
            {"id": "Viper", "nickname": "바이퍼", "real_name": "박도현"},
            {"id": "Delight", "nickname": "딜라이트", "real_name": "유환중"}
        ],
        "coaches": [
            {"id": "Homme", "nickname": "옴므", "real_name": "윤성영"},
            {"id": "Mowgli", "nickname": "모글리", "real_name": "이재하"},
            {"id": "Sin", "nickname": "신", "real_name": "연형모"}
        ]
    },
    "디플러스": {
        "team_names": ["디플러스", "DK", "Dplus KIA", "Dplus", "담원", "DWG", "DK KIA", "딮", "디플", "디플러스기아"],
        "players": [
            {"id": "Siwoo", "nickname": "시우", "real_name": "전시우"},
            {"id": "Lucid", "nickname": "루시드", "real_name": "최용혁"},
            {"id": "ShowMaker", "nickname": "쇼메이커", "real_name": "허수"},
            {"id": "Smash", "nickname": "스매쉬", "real_name": "이준석"},
            {"id": "Career", "nickname": "커리어", "real_name": "최준서"}
        ],
        "coaches": [
            {"id": "cvMax", "nickname": "씨맥", "real_name": "김대호"}
        ]
    },
    "KT": {
        "team_names": ["KT", "kt Rolster", "케이티", "롤스터", "개티", "대퍼팀"],
        "players": [
            {"id": "PerfecT", "nickname": "퍼펙트", "real_name": "이승민"},
            {"id": "Cuzz", "nickname": "커즈", "real_name": "문우찬"},
            {"id": "Bdd", "nickname": "비디디", "real_name": "곽보성"},
            {"id": "Aiming", "nickname": "에이밍", "real_name": "김하람"},
            {"id": "Ghost", "nickname": "고스트", "real_name": "장용준"},
            {"id": "Pollu", "nickname": "폴루", "real_name": "오동규"}
        ],
        "coaches": [
            {"id": "Score", "nickname": "스코어", "real_name": "고동빈"}
        ]
    },
    "피어엑스": {
        "team_names": ["BNK", "BNK FearX", "피어엑스", "FOX", "뱅어엑스", "뱅어스", "피엑"],
        "players": [
            {"id": "Clear", "nickname": "클리어", "real_name": "송현민"},
            {"id": "Raptor", "nickname": "랩터", "real_name": "전어진"},
            {"id": "VicLa", "nickname": "빅라", "real_name": "이대광"},
            {"id": "Daystar", "nickname": "데이스타", "real_name": "유지명"},
            {"id": "Diable", "nickname": "디아블", "real_name": "김진영"},
            {"id": "Taeyoon", "nickname": "태윤", "real_name": "김태윤"},
            {"id": "Kellin", "nickname": "켈린", "real_name": "김형규"}
        ],
        "coaches": [
            {"id": "Edo", "nickname": "에도", "real_name": "박준석"},
            {"id": "Rather", "nickname": "래더", "real_name": "신형섭"},
            {"id": "Lira", "nickname": "리라", "real_name": "남태유"}
        ]
    },
    "DN 수퍼스": {
        "team_names": ["DN SOOPers", "DN 수퍼스", "디엔 수퍼스", "DN 숲퍼스", "SOOP", "숲", "광동", "KDF", "Kwangdong", "프릭스", "숲퍼스", "수퍼스", "DNS"],
        "players": [
            {"id": "DuDu", "nickname": "두두", "real_name": "이동주"},
            {"id": "Pyosik", "nickname": "표식", "real_name": "홍창현"},
            {"id": "Clozer", "nickname": "클로저", "real_name": "이주현"},
            {"id": "deokdam", "nickname": "덕담", "real_name": "서대길"},
            {"id": "Life", "nickname": "라이프", "real_name": "김정민"},
            {"id": "Peter", "nickname": "피터", "real_name": "정윤수"}
        ],
        "coaches": [
            {"id": "oDin", "nickname": "오딘", "real_name": "주영달"},
            {"id": "Ggoong", "nickname": "꿍", "real_name": "유병준"}
        ]
    },
    "DRX": {
        "team_names": ["Kiwoom DRX", "키움 DRX", "키움 디알엑스", "DRX", "디알엑스", "디알", "엑스", "키움디알엑스", "KRX"],
        "players": [
            {"id": "Rich", "nickname": "리치", "real_name": "이재원"},
            {"id": "Willer", "nickname": "윌러", "real_name": "김정현"},
            {"id": "Ucal", "nickname": "유칼", "real_name": "손우현"},
            {"id": "Jiwoo", "nickname": "지우", "real_name": "정지우"},
            {"id": "Vincenzo", "nickname": "빈센조", "real_name": "김정현"},
            {"id": "Andil", "nickname": "안딜", "real_name": "문관빈"}
        ],
        "coaches": [
            {"id": "Joker", "nickname": "조커", "real_name": "조재읍"},
            {"id": "Naehyun", "nickname": "내현", "real_name": "유내현"}
        ]
    },
    "OK저축은행": {
        "team_names": ["Hanjin Brion", "한진 브리온", "한진", "브리온", "BRO", "Brion", "한진브리온"],
        "players": [
            {"id": "Casting", "nickname": "캐스팅", "real_name": "신민제"},
            {"id": "Gideon", "nickname": "기디온", "real_name": "김민성"},
            {"id": "Fisher", "nickname": "피셔", "real_name": "이정태"},
            {"id": "Loki", "nickname": "로키", "real_name": "이상민"},
            {"id": "Teddy", "nickname": "테디", "real_name": "박진성"},
            {"id": "Namgung", "nickname": "남궁", "real_name": "남궁성훈"}
        ],
        "coaches": [
            {"id": "Song", "nickname": "쏭", "real_name": "김상수"},
            {"id": "Duke", "nickname": "듀크", "real_name": "이호성"}
        ]
    },
    "농심": {
        "team_names": ["농심", "NS", "Nongshim", "레드포스", "농심 레드포스", "농"],
        "players": [
            {"id": "Kingen", "nickname": "킹겐", "real_name": "황현서"},
            {"id": "Sponge", "nickname": "스폰지", "real_name": "김관우"},
            {"id": "Scout", "nickname": "스카웃", "real_name": "이예찬"},
            {"id": "Callix", "nickname": "칼릭스", "real_name": "선현빈"},
            {"id": "Taeyoon", "nickname": "태윤", "real_name": "김태윤"},
            {"id": "Lehends", "nickname": "리헨즈", "real_name": "손시우"}
        ],
        "coaches": [
            {"id": "Chelly", "nickname": "첼리", "real_name": "박승진"}
        ]
    },
    # LPL (중국)
    "BLG": {
        "team_names": ["BLG", "Bilibili", "Bilibili Gaming", "빌리빌리", "비엘지"],
        "players": [
            {"id": "Bin", "nickname": "빈", "real_name": "Chen Ze-Bin"},
            {"id": "Xun", "nickname": "슌", "real_name": "Peng Li-Xun"},
            {"id": "Knight", "nickname": "나이트", "real_name": "Zhuo Ding"},
            {"id": "Viper", "nickname": "바이퍼", "real_name": "박도현"},
            {"id": "ON", "nickname": "온", "real_name": "Luo Wen-Jun"}
        ],
        "coaches": [
            {"id": "Daeny", "nickname": "대니", "real_name": "양대인"}
        ]
    },
    "TES": {
        "team_names": ["TES", "Top Esports", "탑이스포츠", "테스", "티이에스", "탑이"],
        "players": [
            {"id": "369", "nickname": "삼육구", "real_name": "Bai Jiahao"},
            {"id": "naiyou", "nickname": "나이요우", "real_name": "Yang Zi-Jian"},
            {"id": "Creme", "nickname": "크림", "real_name": "Jian Lin"},
            {"id": "JiaQi", "nickname": "자치", "real_name": "Runlai Wang"},
            {"id": "fengyue", "nickname": "펑웨이", "real_name": "fengyue"}
        ],
        "coaches": [
            {"id": "Maokai", "nickname": "마오카이", "real_name": "Zhu Kai"}
        ]
    },
    "JDG": {
        "team_names": ["JDG", "JD Gaming", "징동", "징동 게이밍", "제이디지"],
        "players": [
            {"id": "Xiaoxu", "nickname": "샤오쉬", "real_name": "Xu Xing-Zu"},
            {"id": "JunJia", "nickname": "준자", "real_name": "Yu Chun-Chia"},
            {"id": "HongQ", "nickname": "홍큐", "real_name": "Tsai Ming-Hong"},
            {"id": "GALA", "nickname": "갈라", "real_name": "Chen Wei"},
            {"id": "Vampire", "nickname": "뱀파이어", "real_name": "Zhao Zhe-Can"}
        ],
        "coaches": [
            {"id": "Tabe", "nickname": "타베", "real_name": "Wong Pak Kan"}
        ]
    },
    "WBG": {
        "team_names": ["WBG", "Weibo", "Weibo Gaming", "웨이보", "웨이보 게이밍", "더블유비지"],
        "players": [
            {"id": "Zika", "nickname": "지카", "real_name": "Tang Hua-Yu"},
            {"id": "Jiejie", "nickname": "지에지에", "real_name": "Zhao Li-Jie"},
            {"id": "Xiaohu", "nickname": "샤오후", "real_name": "Li Yuan-Hao"},
            {"id": "Elk", "nickname": "엘크", "real_name": "Zhao Jia-Hao"},
            {"id": "Erha", "nickname": "얼하", "real_name": "Shi Xu-Ye"}
        ],
        "coaches": [
            {"id": "Shine", "nickname": "샤인", "real_name": "신동욱"}
        ]
    },
    "EDG": {
        "team_names": ["EDG", "Edward Gaming", "이디지", "에드워드 게이밍"],
        "players": [
            {"id": "Zdz", "nickname": "지디지", "real_name": "Zdz"},
            {"id": "Xiaohao", "nickname": "샤오하오", "real_name": "Xiaohao"},
            {"id": "Sinian", "nickname": "시니안", "real_name": "Sinian"},
            {"id": "Leave", "nickname": "리브", "real_name": "Leave"},
            {"id": "Jwei", "nickname": "제이웨이", "real_name": "Jwei"}
        ],
        "coaches": [
            {"id": "Clearlove", "nickname": "클리어러브", "real_name": "Ming Kai"}
        ]
    },
    "LNG": {
        "team_names": ["LNG", "LNG Esports", "엘엔지"],
        "players": [
            {"id": "sheer", "nickname": "쉬어", "real_name": "sheer"},
            {"id": "Croco", "nickname": "크로코", "real_name": "김동범"},
            {"id": "BuLLDoG", "nickname": "불독", "real_name": "이태영"},
            {"id": "1xn", "nickname": "이안", "real_name": "1xn"},
            {"id": "Missing", "nickname": "미싱", "real_name": "Missing"}
        ],
        "coaches": [
            {"id": "U", "nickname": "유", "real_name": "Zeng Long"}
        ]
    },
    "LGD": {
        "team_names": ["LGD", "LGD Gaming", "엘지디"],
        "players": [
            {"id": "Burdol", "nickname": "버돌", "real_name": "노태윤"},
            {"id": "Heng", "nickname": "헹", "real_name": "Heng"},
            {"id": "Tangyuan", "nickname": "탕위안", "real_name": "Tangyuan"},
            {"id": "Shaoye", "nickname": "샤오예", "real_name": "Shaoye"},
            {"id": "Ycx", "nickname": "와이씨엑스", "real_name": "Ycx"}
        ],
        "coaches": [
            {"id": "1874", "nickname": "일팔칠사", "real_name": "1874"}
        ]
    },
    "NIP": {
        "team_names": ["NIP", "Ninjas in Pyjamas", "닙", "엔아이피"],
        "players": [
            {"id": "Rookie", "nickname": "루키", "real_name": "송의진"}
        ],
        "coaches": [
            {"id": "Zero", "nickname": "제로", "real_name": "윤경섭"}
        ]
    },
    "WE": {
        "team_names": ["WE", "Team WE", "위", "팀위"],
        "players": [
            {"id": "Wayward", "nickname": "웨이워드", "real_name": "Huang Ren-Xing"}
        ],
        "coaches": [
            {"id": "WarHorse", "nickname": "워호스", "real_name": "Chen Ju-Chih"}
        ]
    },
    "AL": {
        "team_names": ["AL", "Anyone's Legend", "에이엘"],
        "players": [
            {"id": "Shanks", "nickname": "샹크스", "real_name": "Ye Ji-Chang"}
        ],
        "coaches": [
            {"id": "Tabe", "nickname": "타베", "real_name": "Wong Pak Kan"}
        ]
    },
    "UP": {
        "team_names": ["UP", "Ultra Prime", "유피", "울트라 프라임"],
        "players": [
            {"id": "Hery", "nickname": "헤리", "real_name": "UP Hery"}
        ],
        "coaches": [
            {"id": "Viento", "nickname": "비엔토", "real_name": "UP Viento"}
        ]
    },
    "OMG": {
        "team_names": ["OMG", "Oh My God", "오엠쥐"],
        "players": [
            {"id": "Angel", "nickname": "엔젤", "real_name": "Xiang Tao"}
        ],
        "coaches": [
            {"id": "Noname", "nickname": "노네임", "real_name": "Zhou Qi-Lin"}
        ]
    },
    "IG": {
        "team_names": ["iG", "Invictus Gaming", "아이쥐", "인빅터스"],
        "players": [
            {"id": "neny", "nickname": "네니", "real_name": "Zhao Zhi-Hao"}
        ],
        "coaches": [
            {"id": "Rasho", "nickname": "라쇼", "real_name": "iG Rasho"}
        ]
    },
    # LEC (유럽)
    "G2": {
        "team_names": ["G2", "G2 Esports", "지투", "지투 이스포츠"],
        "players": [
            {"id": "BrokenBlade", "nickname": "브로큰블레이드", "real_name": "BrokenBlade"},
            {"id": "SkewMond", "nickname": "스큐몬드", "real_name": "SkewMond"},
            {"id": "Caps", "nickname": "캡스", "real_name": "Caps"},
            {"id": "Hans Sama", "nickname": "한스사마", "real_name": "Hans Sama"},
            {"id": "Labrov", "nickname": "라브로브", "real_name": "Labrov"}
        ],
        "coaches": [
            {"id": "Perkz", "nickname": "팍즈", "real_name": "Luka Perković"}
        ]
    },
    "Fnatic": {
        "team_names": ["FNC", "Fnatic", "프나틱", "프낙", "에프엔씨"],
        "players": [
            {"id": "Soboro", "nickname": "소보로", "real_name": "임성민"},
            {"id": "Razork", "nickname": "라조크", "real_name": "Razork"},
            {"id": "Vladi", "nickname": "블라디", "real_name": "Vladi"},
            {"id": "Uset", "nickname": "업셋", "real_name": "Upset"},
            {"id": "Lospa", "nickname": "로스파", "real_name": "Lospa"}
        ],
        "coaches": [
            {"id": "Nightshare", "nickname": "나이트쉐어", "real_name": "Thomas"}
        ]
    },
    "Karmine Corp": {
        "team_names": ["KC", "Karmine Corp", "카민 코프", "케이씨"],
        "players": [
            {"id": "Canna", "nickname": "칸나", "real_name": "김창동"},
            {"id": "Yike", "nickname": "야이크", "real_name": "Yike"},
            {"id": "kyeahoo", "nickname": "계후", "real_name": "kyeahoo"},
            {"id": "Caliste", "nickname": "칼리스테", "real_name": "Caliste"},
            {"id": "Busio", "nickname": "부시오", "real_name": "Busio"}
        ],
        "coaches": [
            {"id": "Reha", "nickname": "레하", "real_name": "Reha"}
        ]
    },
    "Movistar KOI": {
        "team_names": ["MKOI", "Movistar KOI", "모비스타 코이", "코이", "매드 라이온즈", "매드", "MAD"],
        "players": [
            {"id": "Myrwn", "nickname": "미러운", "real_name": "Myrwn"},
            {"id": "Elyoya", "nickname": "엘요야", "real_name": "Elyoya"},
            {"id": "Jojopyun", "nickname": "조조편", "real_name": "Jojopyun"},
            {"id": "Supa", "nickname": "수파", "real_name": "Supa"},
            {"id": "Alvaro", "nickname": "알바로", "real_name": "Alvaro"}
        ],
        "coaches": [
            {"id": "Melzhet", "nickname": "멜젯", "real_name": "Melzhet"}
        ]
    },
    "Team Vitality": {
        "team_names": ["VIT", "Team Vitality", "바이탈리티", "비트"],
        "players": [
            {"id": "Naak Nako", "nickname": "나크나코", "real_name": "Naak Nako"},
            {"id": "Lyncas", "nickname": "링카스", "real_name": "Lyncas"},
            {"id": "Carzzy", "nickname": "카르지", "real_name": "Carzzy"},
            {"id": "Fleshy", "nickname": "플레시", "real_name": "Fleshy"}
        ],
        "coaches": [
            {"id": "Carter", "nickname": "카터", "real_name": "Carter"}
        ]
    },
    "Team Heretics": {
        "team_names": ["TH", "Team Heretics", "헤레틱스", "티에이치"],
        "players": [
            {"id": "Tracyn", "nickname": "트래신", "real_name": "Tracyn"},
            {"id": "Sheo", "nickname": "쉐오", "real_name": "Sheo"},
            {"id": "Serin", "nickname": "세린", "real_name": "Serin"},
            {"id": "Ice", "nickname": "아이스", "real_name": "윤상훈"},
            {"id": "Stend", "nickname": "스텐드", "real_name": "Stend"}
        ],
        "coaches": [
            {"id": "Nukeduck", "nickname": "누크덕", "real_name": "Nukeduck"}
        ]
    },
    "Shifters": {
        "team_names": ["Shifters", "시프터즈", "BDS", "Team BDS", "비디에스"],
        "players": [
            {"id": "Rooster", "nickname": "루스터", "real_name": "신윤환"},
            {"id": "nuc", "nickname": "눅", "real_name": "nuc"},
            {"id": "Paduck", "nickname": "파덕", "real_name": "박현민"},
            {"id": "Trymbi", "nickname": "트림비", "real_name": "Trymbi"}
        ],
        "coaches": [
            {"id": "Striker", "nickname": "스트라이커", "real_name": "Striker"}
        ]
    },
    "SK Gaming": {
        "team_names": ["SK", "SK Gaming", "에스케이", "에스케이 게이밍"],
        "players": [
            {"id": "Wunder", "nickname": "원더", "real_name": "Wunder"},
            {"id": "Skeanz", "nickname": "스키안즈", "real_name": "Skeanz"},
            {"id": "SlowQ", "nickname": "슬로우큐", "real_name": "SlowQ"},
            {"id": "Jopa", "nickname": "조파", "real_name": "Jopa"},
            {"id": "Mikyx", "nickname": "미키엑스", "real_name": "Mikyx"}
        ],
        "coaches": [
            {"id": "Swiffer", "nickname": "스위퍼", "real_name": "Swiffer"}
        ]
    },
    "GIANTX": {
        "team_names": ["GX", "GIANTX", "자이언트엑스", "지엑스"],
        "players": [
            {"id": "Odoamne", "nickname": "오도암네", "real_name": "Odoamne"},
            {"id": "Peach", "nickname": "피치", "real_name": "한민수"}
        ],
        "coaches": [
            {"id": "Kaas", "nickname": "카스", "real_name": "Kaas"}
        ]
    },
    # LCS (북미)
    "Team Liquid": {
        "team_names": ["TL", "Team Liquid", "팀리퀴드", "티엘", "리퀴드"],
        "players": [
            {"id": "Morgan", "nickname": "모건", "real_name": "박루한"},
            {"id": "Josedeodo", "nickname": "호세데오도", "real_name": "Josedeodo"},
            {"id": "Quid", "nickname": "퀴드", "real_name": "임현승"},
            {"id": "Yeon", "nickname": "연", "real_name": "Yeon"},
            {"id": "CoreJJ", "nickname": "코어제이", "real_name": "조용인"}
        ],
        "coaches": [
            {"id": "Spawn", "nickname": "스폰", "real_name": "Jake Tiberi"}
        ]
    },
    "Cloud9": {
        "team_names": ["C9", "Cloud9", "클라우드나인", "씨나인", "클나"],
        "players": [
            {"id": "Thanatos", "nickname": "타나토스", "real_name": "박승규"},
            {"id": "Blaber", "nickname": "블래버", "real_name": "Blaber"},
            {"id": "APA", "nickname": "에이피에이", "real_name": "APA"},
            {"id": "Zven", "nickname": "즈벤", "real_name": "Zven"},
            {"id": "Vulcan", "nickname": "벌칸", "real_name": "Vulcan"}
        ],
        "coaches": [
            {"id": "Inero", "nickname": "이네로", "real_name": "Nick Smith"}
        ]
    },
    "FlyQuest": {
        "team_names": ["FLY", "FlyQuest", "플라이퀘스트", "플라이"],
        "players": [
            {"id": "Gakgos", "nickname": "각고스", "real_name": "Gakgos"},
            {"id": "Gryffinn", "nickname": "그리핀", "real_name": "Gryffinn"},
            {"id": "Quad", "nickname": "쿼드", "real_name": "송수형"},
            {"id": "Massu", "nickname": "마수", "real_name": "Massu"},
            {"id": "Cryogen", "nickname": "크라이오젠", "real_name": "Cryogen"}
        ],
        "coaches": [
            {"id": "Phlox", "nickname": "플록스", "real_name": "Phlox"}
        ]
    },
    "Shopify Rebellion": {
        "team_names": ["SR", "Shopify Rebellion", "쇼피파이", "쇼피파이 리벨리온"],
        "players": [
            {"id": "Fudge", "nickname": "퍼지", "real_name": "Fudge"},
            {"id": "Contractz", "nickname": "컨트랙즈", "real_name": "Contractz"},
            {"id": "Zinie", "nickname": "지니", "real_name": "유백진"},
            {"id": "Bvoy", "nickname": "비보이", "real_name": "주영훈"},
            {"id": "Ceos", "nickname": "세오스", "real_name": "Ceos"}
        ],
        "coaches": [
            {"id": "Reven", "nickname": "레븐", "real_name": "성상현"}
        ]
    },
    "Dignitas": {
        "team_names": ["DIG", "Dignitas", "디그니타스", "디그"],
        "players": [
            {"id": "Photon", "nickname": "포톤", "real_name": "규태민"},
            {"id": "eXyu", "nickname": "엑스유", "real_name": "eXyu"},
            {"id": "Palafox", "nickname": "팔라폭스", "real_name": "Palafox"},
            {"id": "FBI", "nickname": "에프비아이", "real_name": "FBI"},
            {"id": "Ignar", "nickname": "이그나", "real_name": "이동근"}
        ],
        "coaches": [
            {"id": "Zaboutine", "nickname": "자부틴", "real_name": "Zaboutine"}
        ]
    },
    "Sentinels": {
        "team_names": ["SEN", "Sentinels", "센티넬즈", "센티넬"],
        "players": [
            {"id": "tenz", "nickname": "텐즈", "real_name": "Tyson Ngo"}
        ],
        "coaches": [
            {"id": "Kaplan", "nickname": "카플란", "real_name": "Kaplan"}
        ]
    }
}

# e스포츠 대회명 동의어 사전 (First Stand 신설 및 통칭 반영)
TOURNAMENT_SYNONYMS = {
    "롤드컵": ["롤드컵", "월즈", "Worlds", "월드 챔피언십", "World Championship"],
    "MSI": ["MSI", "미드 시즌", "Mid-Season", "미드 시즌 인비테이셔널"],
    "EWC": ["EWC", "이스포츠 월드컵", "Esports World Cup"],
    "KeSPA컵": ["케스파컵", "KeSPA컵", "KeSPA Cup", "케스파"],
    "퍼스트 스탠드": ["퍼스트 스탠드", "First Stand", "FST", "LFS", "퍼스", "퍼스트스탠드"],
    "LCK": ["LCK", "lck", "엘씨케이"],
    "LPL": ["LPL", "lpl", "엘피엘"],
    "LEC": ["LEC", "lec", "엘이씨"],
    "LCS": ["LCS", "lcs", "엘시에스"]
}

# 로스터 실시간 갱신 중복 실행 방지 글로벌 락 플래그
_is_updating_roster = False

class NewsCrawler:
    def __init__(self):
        self.settings = load_settings()
        self.stealth = Stealth()
        # 시작 시 로스터 메모리가 비어있으면 로컬 캐시로 안전 충전
        global TEAM_METADATA
        if not TEAM_METADATA:
            TEAM_METADATA.update(FALLBACK_TEAM_METADATA)

    async def update_rosters_from_namuwiki(self) -> bool:
        """
        나무위키 LCK, LPL, LEC 참가팀 로스터 문서를 실시간 크롤링하여 TEAM_METADATA를 최신화합니다.
        성공 시 기존 데이터를 지우고 덮어쓰며, 실패 시 Fallback 데이터를 로드합니다.
        """
        global TEAM_METADATA, _is_updating_roster
        if _is_updating_roster:
            log_event("ROSTER_UPDATE", "INFO", "이미 실시간 로스터 업데이트 작업이 진행 중입니다. 중복 트리거를 회피합니다.")
            return False
            
        _is_updating_roster = True
        log_event("ROSTER_UPDATE", "INFO", "나무위키 실시간 e스포츠 로스터 파싱을 개시합니다.")
        
        urls = {
            "LCK": "https://namu.wiki/w/League%20of%20Legends%20Champions%20Korea/%EC%B0%B8%EA%B0%80%ED%8C%80%20%EB%A1%9C%EC%8A%A4%ED%84%B0",
            "LPL": "https://namu.wiki/w/League%20of%20Legends%20Pro%20League/%EC%B0%B8%EA%B0%80%ED%8C%80%20%EB%A1%9C%EC%8A%A4%ED%84%B0",
            "LEC": "https://namu.wiki/w/League%20of%20Legends%20EMEA%20Championship/%EC%B0%B8%EA%B0%80%ED%8C%80%20%EB%A1%9C%EC%8A%A4%ED%84%B0"
        }
        new_metadata = {}
        success_league_count = 0
        
        try:
            async with async_playwright() as p:
                try:
                    browser = await p.chromium.launch(
                        headless=True,
                        args=["--disable-blink-features=AutomationControlled"]
                    )
                    context = await browser.new_context(
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    )
                    await self.stealth.apply_stealth_async(context)
                    page = await context.new_page()
                    page.set_default_timeout(15000)
                    
                    for league, url in urls.items():
                        try:
                            log_event("ROSTER_UPDATE", "INFO", f"{league} 로스터 수집 중...")
                            await page.goto(url)
                            await page.wait_for_timeout(3000)
                            
                            html = await page.content()
                            soup = BeautifulSoup(html, "lxml")
                            tables = soup.find_all("table", class_="wiki-table")
                            
                            for table in tables:
                                rows = table.find_all("tr")
                                if not rows:
                                    continue
                                    
                                # 테이블 헤더 또는 상단 텍스트에서 LCK/LPL/LEC 기존 정의된 팀명 매칭 시도
                                team_found_key = None
                                for key, meta in FALLBACK_TEAM_METADATA.items():
                                    if any(name.lower() in table.text.lower() for name in meta["team_names"]):
                                        team_found_key = key
                                        break
                                        
                                if not team_found_key:
                                    continue
                                    
                                # 수집 데이터 초기화 (처음 매칭 시에만 생성)
                                if team_found_key not in new_metadata:
                                    new_metadata[team_found_key] = {
                                        "team_names": FALLBACK_TEAM_METADATA[team_found_key]["team_names"],
                                        "players": [],
                                        "coaches": []
                                    }
                                    
                                for row in rows:
                                    cells = row.find_all(["td", "th"])
                                    if len(cells) < 2:
                                        continue
                                        
                                    pos_text = cells[0].text.strip()
                                    cont_text = cells[1].text.strip()
                                    
                                    is_coach = any(kw in pos_text for kw in ["감독", "코치", "Coach", "Head Coach", "코칭스태프"])
                                    is_player = any(kw in pos_text for kw in ["Top", "Jungle", "Mid", "Bot", "Support", "ADC", "탑", "정글", "미드", "바텀", "서포터"])
                                    
                                    if not (is_coach or is_player):
                                        continue
                                        
                                    # "Faker(이상혁)" 혹은 "Faker (이상혁)" 혹은 "Faker\n이상혁" 매칭
                                    matches = re.findall(r"([a-zA-Z0-9_-]{2,15})\s*\(([^)]+)\)", cont_text)
                                    if not matches:
                                        # 줄바꿈 분할 매치 시도
                                        parts = re.split(r"[\n/]", cont_text)
                                        if len(parts) >= 2:
                                            p_nick = re.sub(r"[^a-zA-Z0-9_-]", "", parts[0]).strip()
                                            p_real = re.sub(r"[^가-힣a-zA-Z]", "", parts[1]).strip()
                                            if len(p_nick) >= 2 and len(p_real) >= 2:
                                                matches = [(p_nick, p_real)]
                                                
                                    for nick, real in matches:
                                        if is_player:
                                            new_metadata[team_found_key]["players"].append({
                                                "id": nick,
                                                "nickname": nick,
                                                "real_name": real
                                            })
                                        elif is_coach:
                                            new_metadata[team_found_key]["coaches"].append({
                                                "id": nick,
                                                "nickname": nick,
                                                "real_name": real
                                            })
                            
                            success_league_count += 1
                            
                        except Exception as le:
                            log_event("ROSTER_UPDATE", "WARNING", f"{league} 리그 로스터 수집 중 오류 발생 (스킵): {str(le)}")
                            
                    await browser.close()
                    
                except Exception as e:
                    log_event("ROSTER_UPDATE", "WARNING", f"나무위키 브라우저 가동 실패: {str(e)}")
        finally:
            _is_updating_roster = False
            
        # 섞임 없이 전체 덮어쓰기 적용
        if success_league_count > 0 and len(new_metadata) >= 3:
            TEAM_METADATA.clear()
            TEAM_METADATA.update(new_metadata)
            log_event("ROSTER_UPDATE", "SUCCESS", f"나무위키 최신화 완수! {success_league_count}개 리그, 총 {len(TEAM_METADATA)}개 팀 갱신 완료.")
            return True
        else:
            TEAM_METADATA.clear()
            TEAM_METADATA.update(FALLBACK_TEAM_METADATA)
            log_event("ROSTER_UPDATE", "WARNING", "나무위키 실시간 수집에 실패하여 Fallback 로컬 캐시를 활성화했습니다.")
            return False

    async def collect_and_process_news(self) -> int:
        """
        네이버 e스포츠 뉴스를 수집하고 필터링한 뒤, 요약 및 원문 아카이빙을 수행하여 카페에 자동 게시합니다.
        """
        self.settings = load_settings()
        target_url = self.settings.news.target_url
        
        # 0. 기사 수집 직전에 나무위키 로스터 실시간 동기화 수행 (동적 2부 콜업 및 최신 데이터 반영)
        await self.update_rosters_from_namuwiki()
        
        log_event("NEWS_SCRAPING", "INFO", "e스포츠 뉴스 수집을 시작합니다.")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800}
            )
            await self.stealth.apply_stealth_async(context)
            page = await context.new_page()
            
            try:
                # 1. 기사 목록 수집
                await page.goto(target_url)
                # 기사 로딩을 위해 5초 대기
                await page.wait_for_timeout(5000)
                
                # HTML 파싱
                content = await page.content()
                soup = BeautifulSoup(content, "lxml")
                
                # 뉴스 카드 링크와 제목 수집 (범용 href 기반 셀렉터로 개편하여 0개 수집 이슈 해결)
                articles = []
                card_links = soup.select('a[href*="/article/"]:not([class*="mostview"])')
                
                # 중복 방지를 위한 set
                seen_urls = set()
                
                for link in card_links:
                    href = link.get("href")
                    if not href:
                        continue
                    
                    # 상대 경로 주소 보완
                    full_url = urljoin("https://game.naver.com", href)
                    
                    if full_url in seen_urls:
                        continue
                    seen_urls.add(full_url)
                    
                    # 제목 추출 (카드 내부의 strong 태그 텍스트 획득)
                    title_el = link.select_one('strong')
                    title = title_el.text.strip() if title_el else ""
                    if not title:
                        continue
                        
                    # 기사 ID 추출 (URL에서 숫자 ID 파싱)
                    # 예: https://game.naver.com/esports/article/468/0001254488
                    article_id = "unknown"
                    id_match = re.search(r"article/(\d+/\d+|\d+)", full_url)
                    if id_match:
                        article_id = id_match.group(1).replace("/", "_")
                    else:
                        # 모바일/다른 형태의 주소 매칭
                        id_match_alt = re.search(r"article[?/]id=(\d+)", full_url)
                        if id_match_alt:
                            article_id = id_match_alt.group(1)
                            
                    articles.append({
                        "id": article_id,
                        "title": title,
                        "url": full_url
                    })
                    
                log_event("NEWS_SCRAPING", "INFO", f"총 {len(articles)}개의 기사 후보를 수집했습니다.")
                
                if not articles:
                    log_event("NEWS_SCRAPING", "WARNING", "수집된 기사 목록이 비어 있습니다.")
                    await browser.close()
                    return 0
                    
                # 2. 필터링 로직 적용 (팀별 균등 분배 + 인터뷰 우선순위)
                filtered_articles = self._filter_articles(articles)
                log_event("NEWS_SCRAPING", "INFO", f"필터링을 거쳐 최종 {len(filtered_articles)}개의 기사를 선정했습니다.")
                
                # 3. 각 기사별 상세 수집, 아카이빙 및 게시
                from backend.naver_bot import NaverCafeBot
                bot = NaverCafeBot()
                
                success_count = 0
                db = SessionLocal()
                
                for art in filtered_articles:
                    # 이미 아카이빙된 기사인지 체크
                    existing = db.query(NewsArchive).filter(NewsArchive.article_id == art["id"]).first()
                    if existing:
                        log_event("NEWS_SCRAPING", "INFO", f"이미 처리된 기사입니다. 스킵: {art['title']}")
                        continue
                        
                    # 상세 페이지 접속하여 본문 및 이미지 수집
                    detail_data = await self._scrape_article_detail(page, art["url"], art["id"])
                    if not detail_data:
                        continue
                        
                    # 본문 요약 적용
                    summary = self._summarize_content(detail_data["raw_text"])
                    
                    # DB 아카이브 등록
                    archive = NewsArchive(
                        article_id=art["id"],
                        title=art["title"],
                        summary=summary,
                        source_url=art["url"],
                        local_path=detail_data["archive_path"],
                        published_at=datetime.now()
                    )
                    db.add(archive)
                    db.commit()
                    
                    # 네이버 카페에 기사 등록
                    post_res = await bot.write_news_article(art["title"], summary, art["url"])
                    if post_res.get("status") == "SUCCESS":
                        success_count += 1
                        log_event("NEWS_SCRAPING", "SUCCESS", f"기사 발행 완료: {art['title']}")
                    else:
                        log_event("NEWS_SCRAPING", "FAILED", f"기사 발행 실패: {art['title']}, 사유: {post_res.get('message')}")
                        
                    # 카페 글쓰기 사이의 랜덤 지연 (봇 방지)
                    await page.wait_for_timeout(3000)
                    
                db.close()
                await browser.close()
                return success_count
                
            except Exception as e:
                log_event("NEWS_SCRAPING", "FAILED", f"뉴스 수집/처리 과정 중 심각한 에러 발생: {str(e)}")
                await browser.close()
                return 0

    def _filter_articles(self, articles: List[Dict[str, Any]], limit: int = 10) -> List[Dict[str, Any]]:
        """
        팀별 동의어 및 대회 키워드를 정밀 판정하고, 균등 분배 및 인터뷰 우선순위를 고려하여 기사를 최종 필터링합니다.
        """
        teams = self.settings.news.teams
        interview_kws = self.settings.news.interview_keywords
        
        # 1. 각 기사에 대해 팀 소속, 대회 태그 및 인터뷰 여부 판정
        classified = []
        for art in articles:
            title = art["title"]
            title_lower = title.lower()
            
            # 인터뷰 여부 판별 (선수/감독명 등 정밀화)
            is_interview = any(kw in title for kw in interview_kws)
            if "[인터뷰]" in title or "인터뷰" in title or "대담" in title:
                is_interview = True
                
            # 대회 매칭 태깅 (부가 정보용)
            matched_tournaments = []
            for tour_key, tour_syns in TOURNAMENT_SYNONYMS.items():
                if any(syn.lower() in title_lower for syn in tour_syns):
                    matched_tournaments.append(tour_key)
            
            # 소속 팀 판별 (TEAM_METADATA 계층 카테고리 순회)
            assigned_team = "일반"
            for team_key, meta in TEAM_METADATA.items():
                # 1) 팀명 매핑 체크
                if any(syn.lower() in title_lower for syn in meta["team_names"]):
                    assigned_team = team_key
                    break
                
                # 2) 선수 닉네임 / 본명 매핑 체크
                player_matched = False
                for p in meta["players"]:
                    if p["nickname"].lower() in title_lower or p["real_name"].lower() in title_lower:
                        player_matched = True
                        break
                if player_matched:
                    assigned_team = team_key
                    break
                    
                # 3) 코칭스태프 닉네임 / 본명 매핑 체크
                coach_matched = False
                for c in meta["coaches"]:
                    if c["nickname"].lower() in title_lower or c["real_name"].lower() in title_lower:
                        coach_matched = True
                        break
                if coach_matched:
                    assigned_team = team_key
                    break
                    
            if assigned_team == "일반":
                # 팀 분류에 실패(일반 기사로 귀속)했을 경우 디스코드 웹훅 알림 발송
                try:
                    from backend.discord_notifier import notify_team_classification_failure
                    notify_team_classification_failure(
                        article_title=title,
                        article_link=art["url"],
                        error_msg="기사 제목에 매칭되는 2026시즌 e스포츠 팀명, 선수 닉네임/본명 또는 코칭스태프가 로스터 메타데이터 사전에 등록되어 있지 않습니다."
                    )
                except Exception as de:
                    log_event("NEWS_SCRAPING", "WARNING", f"디스코드 분류 실패 알림 전송 실패: {str(de)}")

            classified.append({
                **art,
                "team": assigned_team,
                "tournaments": matched_tournaments,
                "is_interview": is_interview
            })
            
        # 2. 정렬 순서: 인터뷰 기사를 최우선으로 배치
        classified.sort(key=lambda x: (x["is_interview"], x["team"] != "일반"), reverse=True)
        
        # 3. 팀별 균등 분배 수집 알고리즘
        # 특정 인기 팀이 도배되는 것을 방지하기 위해, 동일 팀 기사는 최대 2개로 제한
        team_counts = {}
        for team_key in TEAM_METADATA.keys():
            team_counts[team_key] = 0
        team_counts["일반"] = 0
        
        final_list = []
        for art in classified:
            team = art["team"]
            
            # 사전에 없는 기타 팀명 처리용 초기화
            if team not in team_counts:
                team_counts[team] = 0
                
            # 이미 동일 팀 기사가 2개 이상 선택되었다면 스킵 (균등 배분)
            if team != "일반" and team_counts[team] >= 2:
                continue
            # 일반 기사도 3개 이상 선택 시 스킵
            if team == "일반" and team_counts["일반"] >= 3:
                continue
                
            final_list.append(art)
            team_counts[team] += 1
            
            if len(final_list) >= limit:
                break
                
        return final_list

    async def _scrape_article_detail(self, page, url: str, article_id: str) -> Optional[Dict[str, Any]]:
        """기사 상세 페이지를 로드하여 본문 텍스트를 파싱하고 본문 내 이미지를 로컬에 저장합니다."""
        try:
            await page.goto(url)
            await page.wait_for_timeout(3000)
            
            # 본문 영역 파싱 (네이버 스포츠 PC/모바일 및 React 개편 랩퍼 전수 탐색)
            body_selector = "#newsct_article, #articeBody, .news_end, div[class*='NewsEnd_article_body'], div[class*='article_body'], #news_body_area, #newsct"
            body_el = await page.query_selector(body_selector)
            if not body_el:
                log_event("NEWS_SCRAPING", "WARNING", f"기사 본문 요소를 찾지 못했습니다: {url}")
                return None
                
            raw_text = await body_el.inner_text()
            raw_html = await body_el.inner_html()
            
            # 아카이빙 디렉터리 생성: data/archive/{article_id}/
            art_dir = os.path.join(ARCHIVE_DIR, article_id)
            img_dir = os.path.join(art_dir, "images")
            os.makedirs(img_dir, exist_ok=True)
            
            # BeautifulSoup을 통해 HTML 내부 이미지 추출 및 저장
            soup = BeautifulSoup(raw_html, "lxml")
            imgs = soup.find_all("img")
            
            # 이미지 다운로드 및 로컬 주소 치환
            img_counter = 1
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            # 비동기 HTTP 클라이언트 가동
            async with httpx.AsyncClient(headers=headers, timeout=10.0) as client:
                for img in imgs:
                    src = img.get("src") or img.get("data-src")
                    if not src or not src.startswith("http"):
                        continue
                        
                    try:
                        # 이미지 다운로드
                        response = await client.get(src)
                        if response.status_code == 200:
                            # 확장자 판별
                            ext = "jpg"
                            if ".png" in src.lower():
                                ext = "png"
                            elif ".gif" in src.lower():
                                ext = "gif"
                                
                            img_filename = f"img_{img_counter}.{ext}"
                            img_path = os.path.join(img_dir, img_filename)
                            
                            with open(img_path, "wb") as f:
                                f.write(response.content)
                                
                            # HTML 상의 src 주소를 로컬 주소(상대경로)로 변경
                            img["src"] = f"./images/{img_filename}"
                            img_counter += 1
                    except Exception as e:
                        # 이미지 개별 다운로드 실패는 전체 본문 수집 실패로 잡지 않고 무시
                        pass
            
            # 로컬 경로로 수정된 HTML을 기반으로 Markdown 생성
            modified_html = str(soup)
            markdown_content = f"# 기사 원문\n\n**출처 URL:** {url}\n\n"
            
            # HTML을 간단히 텍스트화 및 이미지 마크다운 구문 추가
            # BeautifulSoup에서 텍스트와 이미지 태그를 순서대로 파싱하여 마크다운 파일 작성
            for child in soup.children:
                if child.name == "img" and child.get("src"):
                    markdown_content += f"\n![기사 이미지]({child['src']})\n\n"
                elif child.name in ["p", "div", "span"] or not child.name:
                    text = child.get_text().strip()
                    if text:
                        markdown_content += f"{text}\n\n"
                        
            # 마크다운 저장
            md_path = os.path.join(art_dir, "article.md")
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)
                
            # HTML 원본도 보존 (더 원활한 UI 렌더링용)
            html_path = os.path.join(art_dir, "article.html")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(f"<html><head><meta charset='UTF-8'></head><body>{modified_html}</body></html>")
                
            relative_archive_path = f"data/archive/{article_id}/article.md"
            
            return {
                "raw_text": raw_text,
                "archive_path": relative_archive_path
            }
            
        except Exception as e:
            log_event("NEWS_SCRAPING", "WARNING", f"기사 본문 상세 수집 오류 ({url}): {str(e)}")
            return None

    def _summarize_content(self, text: str) -> str:
        """기사 본문을 원본의 50% 미만으로 요약합니다. LLM 또는 무료 알고리즘 적용."""
        use_llm = self.settings.news.use_llm_summary
        api_key = self.settings.news.openai_api_key
        
        if use_llm and api_key:
            try:
                # LLM API 동기 호출 (httpx로 요청)
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": "너는 e스포츠 전문 뉴스 요약봇이야. 제시된 뉴스 본문을 주요 내용 위주로 정리해줘. 단, 절대로 원문 길이의 45%를 넘기지 말아야 하고, 간결한 리포트 형식으로 3~5개 핵심 문단으로 정리해야 해. 출처 링크는 본문에 직접 넣지 마."},
                        {"role": "user", "content": f"요약할 뉴스 기사 본문:\n{text}"}
                    ],
                    "temperature": 0.5
                }
                
                with httpx.Client(timeout=30.0) as client:
                    response = client.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers)
                    if response.status_code == 200:
                        res_data = response.json()
                        summary_text = res_data["choices"][0]["message"]["content"].strip()
                        
                        # 분량이 50%를 초과하는지 자가 검증 후 초과 시 하향 폴백
                        if len(summary_text) < len(text) * 0.5:
                            return summary_text
                            
            except Exception as e:
                log_event("NEWS_SCRAPING", "WARNING", f"OpenAI API 요약 실패 (무료 알고리즘으로 대체): {str(e)}")
                
        # --- 무료 알고리즘 방식 ---
        # 1. 줄 바꿈 및 마침표 기준으로 문장 추출
        # 기사의 앞부분 및 핵심 정보가 많은 상위 30% 문장을 추출하여 자연스럽게 조합
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        
        # 기사 작성자 정보, 불필요한 저작권 정보 등 하단 스킵용 필터링
        filtered_lines = []
        for line in lines:
            if "기자 =" in line or "기자=" in line or "무단전재" in line or "배포금지" in line or "Copyrights" in line:
                continue
            filtered_lines.append(line)
            
        # 전체 문단 중 앞의 4~6개 주요 문단만 결합하여 본문 분량의 50% 미만 보장
        summary_lines = []
        current_len = 0
        max_len = len(text) * 0.45 # 최대 45%까지만 허용
        
        for line in filtered_lines:
            if current_len + len(line) < max_len:
                summary_lines.append(line)
                current_len += len(line) + 1
            else:
                break
                
        if not summary_lines:
            # 예외 대비 상위 3문장만 리턴
            summary_lines = filtered_lines[:3]
            
        summary_result = "\n\n".join(summary_lines)
        if len(summary_result) < len(text):
            summary_result += "\n\n..."
            
        return summary_result
