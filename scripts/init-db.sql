-- Initialize schemas for Payment Lab and SentinelQA
CREATE SCHEMA IF NOT EXISTS payment_lab;
CREATE SCHEMA IF NOT EXISTS sentinelqa;

-- Set default search path
ALTER DATABASE sentinelqa SET search_path TO payment_lab, public;
