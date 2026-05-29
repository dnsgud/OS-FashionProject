create table wishlist (
  id uuid default gen_random_uuid() primary key,
  user_id uuid not null, -- 유저 테이블의 id 유형에 맞춤
  top_combo jsonb not null, -- 상의 조합 데이터 (이너/아우터 배열 형태를 통째로 저장)
  bottom jsonb not null,    -- 하의 데이터 객체 저장
  fashion_score int4,
  style_score int4,
  color_score int4,
  temp_score int4,
  wear_score int4,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);
