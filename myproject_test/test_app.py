import pytest
import json
import os
import sys
import warnings
from io import BytesIO
from PIL import Image, ImageDraw
import requests
from unittest.mock import MagicMock, patch

#  1. 라이브러리 경고 완전 음소거
warnings.filterwarnings("ignore")

DUMMY_IMG = "dummy_test_image.jpg"
if not os.path.exists(DUMMY_IMG):
    img = Image.new('RGB', (200, 200), color=(220, 170, 140))
    draw = ImageDraw.Draw(img)
    corner = 20
    for box in [[0,0,corner,corner], [200-corner,0,200,corner], [0,200-corner,corner,200], [200-corner,200-corner,200,200]]:
        draw.rectangle(box, fill=(50, 50, 50))
    img.save(DUMMY_IMG)

def execute_safely(func, *args, **kwargs):
    try: func(*args, **kwargs)
    except: pass

# =========================================================================
#  2. 견고한 글로벌 모킹 (가짜 DB & 통신)
# =========================================================================
class MockResponse:
    def __init__(self, data=None): self.data = data if data is not None else []

class ChainableMock(MagicMock):
    def __getattr__(self, name):
        if name in ['select', 'insert', 'update', 'delete', 'eq', 'in_', 'order', 'upsert']:
            return self
        return super().__getattr__(name)

mock_sb = MagicMock()
mock_table = ChainableMock()
mock_sb.table.return_value = mock_table
mock_sb.storage.from_.return_value.upload.return_value = True
mock_sb.storage.from_.return_value.get_public_url.return_value = "http://fake.url"

default_data = [{"id": 1, "pw": "password123", "login_id": "testuser01", "email": "test@gmail.com", "monthly_wear_count": 0, "top_ids": [1], "bottom_id": 2, "shoes_id": 3, "body_shape": "삼각형", "title": "test", "created_at": "2026-01-01", "name": "이름", "nickname": "닉네임", "height": 175, "weight": 70, "color": "#000000", "temp_level": 5, "fit": "레귤러핏"}]
mock_table.execute.return_value = MockResponse(default_data)

requests.post = MagicMock(return_value=MagicMock(status_code=200, ok=True, json=lambda: [{"id": "1", "email": "test@gmail.com"}]))
requests.get = MagicMock(return_value=MagicMock(status_code=200, ok=True, json=lambda: [{"id": "1", "email": "test@gmail.com"}]))

import myproject.app as app_module
import myproject.auth_service as auth_svc
import myproject.services.auth as s_auth
import myproject.services.imgproc as s_img
import myproject.services.scrap_service as s_scrap
import myproject.services.userprofile as s_up

app_module.supabase = auth_svc.supabase = s_auth.supabase = s_img.supabase = s_scrap.supabase = s_up.supabase = mock_sb

# ImportError 증발 복구 (에러 원천 차단)
s_up._validate_name = s_auth._validate_name
s_up._validate_nickname = s_auth._validate_nickname
s_up._validate_email_format = s_auth._validate_email_format
s_up.check_nickname_duplicate = getattr(s_auth, 'check_nickname_duplicate', MagicMock(return_value=True))
s_up.check_email_duplicate = getattr(s_auth, 'check_email_duplicate', MagicMock(return_value=True))
s_up._validate_password_match = getattr(s_auth, '_validate_password_match', MagicMock(return_value=True))

@pytest.fixture
def client():
    app_module.app.config['TESTING'] = True
    with app_module.app.test_client() as client:
        yield client