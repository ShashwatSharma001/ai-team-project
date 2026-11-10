-- Create the "dw" (data warehouse) dataset that holds the star schema.
-- IF NOT EXISTS: running this again does nothing.
CREATE SCHEMA IF NOT EXISTS dw
OPTIONS (location = 'US');
