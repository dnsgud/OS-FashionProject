-- 1. 이미지 주소를 저장할 컬럼 추가
ALTER TABLE clothes ADD COLUMN IF NOT EXISTS image_url TEXT;

-- 2. AI가 분석한 원본 태그들을 저장할 컬럼 추가
-- 예: ['black', 'cotton', 'hoodie']
ALTER TABLE clothes ADD COLUMN IF NOT EXISTS ai_tags TEXT[];

-- 3. AI 분석 결과가 정확한지 유저가 확인했는지 여부 (기본값 false)
ALTER TABLE clothes ADD COLUMN IF NOT EXISTS is_verified BOOLEAN DEFAULT false;