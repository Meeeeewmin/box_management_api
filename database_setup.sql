# database_setup.sql
-- MariaDB 데이터베이스 및 사용자 생성
CREATE DATABASE IF NOT EXISTS edge_computer_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 사용자 생성 및 권한 부여 (실제 환경에서는 강력한 비밀번호 사용)
CREATE USER IF NOT EXISTS 'edge_user'@'localhost' IDENTIFIED BY 'edge_password_2024!';
GRANT ALL PRIVILEGES ON edge_computer_db.* TO 'edge_user'@'localhost';
FLUSH PRIVILEGES;
