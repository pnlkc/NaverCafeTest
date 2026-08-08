import sys
import os
import subprocess
import time
import signal

# Windows 콘솔 한글 깨짐 방지 파이썬 표준 스트림 설정
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# 현재 경로를 프로젝트 루트로 지정
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROJECT_ROOT)

print("=" * 60)
print(" 🤖 네이버 카페 자동 관리 통합 제어 시스템 가동 중...")
print("=" * 60)


processes = []

def kill_child_processes():
    """실행 중인 모든 하위 프로세스를 안전하게 강제 종료합니다."""
    print("\n[안내] 모든 카페 관리 서버 프로세스를 안전하게 정지하고 자원을 반납합니다...")
    for proc in processes:
        if proc.poll() is None:  # 아직 실행 중인 경우
            try:
                if sys.platform == "win32":
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    proc.terminate()
                    proc.wait(timeout=3)
            except Exception as e:
                print(f"[경고] 프로세스 정지 중 일부 예외 발생 (PID {proc.pid}): {e}")
    print("[완료] 네이버 카페 자동 관리 시스템이 정지되었습니다. 이용해 주셔서 감사합니다.")

def signal_handler(sig, frame):
    kill_child_processes()
    sys.exit(0)

# 시그널 핸들러 등록 (Ctrl+C 및 종료 시그널 감지)
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def clean_occupying_ports():
    """8000번 및 5173번 포트를 이미 점유하고 있는 잔존 프로세스를 구동 전 자동으로 정리합니다."""
    print("[시스템] 서비스 준비 중: 이전 점유 포트(8000, 5173) 자동 정리 완료")
    if sys.platform == "win32":
        try:
            cmd = "for /f \"tokens=5\" %a in ('netstat -aon ^| findstr :8000') do taskkill /F /PID %a"
            subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            cmd_fe = "for /f \"tokens=5\" %a in ('netstat -aon ^| findstr :5173') do taskkill /F /PID %a"
            subprocess.run(cmd_fe, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

# 구동 전 남아있는 포트 자동 릴리즈 실행
clean_occupying_ports()

try:
    # 1. 백엔드 FastAPI 서버 구동 (가상환경 파이썬 사용)
    backend_cmd = [
        os.path.join(PROJECT_ROOT, "venv", "Scripts", "python.exe"),
        "-m", "uvicorn", 
        "backend.main:app", 
        "--host", "0.0.0.0", 
        "--port", "8000"
    ]
    print("[시스템] 백엔드 메인 엔진 및 자동 스케줄러 서버를 시작합니다 (8000 포트)...")
    backend_proc = subprocess.Popen(
        backend_cmd, 
        cwd=PROJECT_ROOT,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
    )
    processes.append(backend_proc)

    # 2. 프론트엔드 Vite 개발 서버 구동
    frontend_dir = os.path.join(PROJECT_ROOT, "frontend")
    frontend_cmd = "npm run dev"
    print("[시스템] 프론트엔드 웹 대시보드 화면 서버를 시작합니다 (5173 포트)...")
    
    frontend_proc = subprocess.Popen(
        frontend_cmd, 
        cwd=frontend_dir, 
        shell=True,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
    )
    processes.append(frontend_proc)

    print("\n" + "=" * 60)
    print(" 🎉 [가동 완료] 네이버 카페 자동 관리 시스템이 활성화되었습니다.")
    print(" 📌 관리자 웹 페이지 접속: http://localhost:8000 (통합 대시보드 화면)")
    print(" 📌 실시간 개발용 접속 주소: http://localhost:5173 (화면 실시간 편집용)")
    print(" ※ 이 콘솔 창을 닫거나 Ctrl+C 키를 누르면 모든 자동 관리 기능이 안전하게 정지됩니다.")
    print("=" * 60 + "\n")

    # 서버 상태 무한 감시 루프
    while True:
        time.sleep(2)
        
        # 프로세스 상태 체크
        for name, proc in [("백엔드 엔진", backend_proc), ("웹 대시보드 화면", frontend_proc)]:
            exit_code = proc.poll()
            if exit_code is not None:
                print(f"\n[주의] {name} 서버가 정지되었습니다. (종료 코드: {exit_code})")
                raise KeyboardInterrupt  # 루프 이탈 후 클린업 트리거

except KeyboardInterrupt:
    kill_child_processes()
except Exception as e:
    print(f"[시스템] 시스템 모니터링 중 예외 발생: {e}")
    kill_child_processes()

