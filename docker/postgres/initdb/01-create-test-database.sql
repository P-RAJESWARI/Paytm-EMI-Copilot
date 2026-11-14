-- Runs once, when the PostgreSQL data volume is first created (ADR 0007).
-- Integration tests use this separate database so they never touch development data.
CREATE DATABASE emi_copilot_test;
