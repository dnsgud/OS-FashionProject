# 👔 Smart Climate Fashion System



---

## 💾 1. 설치 방법

### 원격 저장소 복제 및 의존성 설치

```bash
git clone https://github.com/dnsgud/OS-FashionProject.git
cd myproject
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

---

## 📦 2. 의존성 

### OS 및 런타임 환경

1. **OS:** Ubuntu 22.04 LTS / macOS Sonoma / Windows 11
2. **Python:** v3.10.x 이상
3. **Node.js:** v18.x.x 이상

### 핵심 프레임워크 및 외부 라이브러리

프로젝트에 활용된 주요 외부 GitHub 패키지들을 방문하여 생태계 상생을 위한 **'Star(⭐)'** 등록을 모두 완료하였다.

1. **Flask (v3.0.0) & Flask-CORS (v6.0.2):** API 서버 구축 및 CORS 제어
2. **Supabase (v2.30.0):** 실시간 데이터베이스 연동 및 Auth 관리
3. **PyTorch (v2.12.0) & Torchvision (v0.27.0):** 딥러닝 인프라 구동
4. **Transformers (v5.9.0):** 최신 AI 모델 파이프라인 활용 [[GitHub ⭐](https://github.com/huggingface/transformers)]
5. **Rembg (v2.0.74):** 자동 배경 제거(누끼) 모듈 활용 [[GitHub ⭐](https://github.com/danielgatis/rembg)]
6. **OpenCV & Open_CLIP_Torch (v3.3.0):** 이미지 전처리 및 특징 추출 [[GitHub ⭐](https://github.com/mlfoundations/open_clip)]

---

## ✏️ 3. 사용(실행) 방법 

### 백엔드 서버 및 외부 포워딩 실행

1. `myproject/` 폴더 내에 `.env`와 `.mail_env` 파일 생성 후 보안 토큰 기입 (환경 변수 문의: 0301qls@naver.com)
2. 아래 명령어 박스의 코드를 순차적으로 실행하여 로컬 서버 가동 및 ngrok 외부 포워딩 실행
3. ngrok을 통해 만들어진 Forwarding 주소로 외부 브라우저 접속하여 사이트 확인

```bash
python app.py
ngrok config add-authtoken [메일로_전달된_토큰_값]
ngrok http 5000
```

### [중요] Unit Test 실행 방법

1. 가상환경이 활성화된 상태인지 확인
2. 아래 명령어를 실행하여 유닛 테스트 무결성 검증

```bash
pytest
```

---

## 📜 4. 라이선스 및 개발진 

### 개발진 명단 (Contributor 실명)

1. **Gichan (권기찬)** -  ai 사진분석 알고리즘 및 프로필, 회원가입 로직 담당
2. **[0301qls] (남현빈)** - 백엔드 설계 담당
3. **[dnsgud] (정운형)** - 코디 추천 알고리즘 및 코디 저장 알고리즘 담당
4. **[Cross1406] (곽예찬)** - 프론트엔드 UI 디자인 및 UX 구성

### 라이선스 명세

1. 본 프로젝트는 **Apache License 2.0**을 따른다.
2. 라이선스 전문은 아래와 같으며, 프로젝트 루트의 `LICENSE` 파일에서도 확인 가능하다.

```text
Copyright 2026 OS-FashionProject

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    [http://www.apache.org/licenses/LICENSE-2.0](http://www.apache.org/licenses/LICENSE-2.0)

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```
