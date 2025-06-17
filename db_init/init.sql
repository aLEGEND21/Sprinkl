-- init.sql
-- This script will be executed by Docker Compose when the MariaDB container starts for the first time.
-- It sets up the database schema for the AI-powered food app.

-- Create the main database
CREATE DATABASE IF NOT EXISTS foodapp_db;
USE foodapp_db;

-- 1. Recipes Table
-- Stores all the recipe information from your CSV dataset.
-- 'id' will be a unique identifier for each recipe.
-- JSON types are used for 'cleaned_ingredients' and 'feature_vector' to store
-- structured array data that will be processed by your ML backend.
CREATE TABLE IF NOT EXISTS recipes (
    id VARCHAR(255) PRIMARY KEY,
    recipe_name VARCHAR(255) NOT NULL,
    ingredient_measurements JSON, -- Stores each ingredient along with its measurement
    time_mins INT,
    cuisine VARCHAR(100),
    instructions TEXT,
    recipe_url TEXT,
    ingredient_list JSON, -- Stores an array of all the ingredients used in the recipe
    image_url TEXT,
    ingredient_count INT,
    feature_vector JSON -- Stores the numerical vector representation of the recipe for ML
);

-- 2. Users Table
-- Stores unique user IDs. These IDs will typically come from your mobile app's authentication
-- (e.g., Firebase Auth UID, or a UUID generated locally).
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(255) PRIMARY KEY
);

-- 3. User Feedback Table
-- Records when a user likes or dislikes a specific recipe.
-- A composite primary key ensures a user can only have one feedback entry per recipe.
CREATE TABLE IF NOT EXISTS user_feedback (
    user_id VARCHAR(255) NOT NULL,
    recipe_id VARCHAR(255) NOT NULL,
    feedback_type ENUM('like', 'dislike') NOT NULL, -- 'like' or 'dislike'
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, recipe_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
);

-- 4. Recommendations Table
-- Stores pre-calculated recommendations for each user. Your ML API will update this table.
-- 'recommended_recipe_ids' stores an ordered JSON array of recipe IDs.
CREATE TABLE IF NOT EXISTS recommendations (
    user_id VARCHAR(255) PRIMARY KEY,
    recommended_recipe_ids JSON, -- Stores an array of recipe IDs that are recommended for this user
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, -- Automatically updates on change
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Optional: Create an index for faster lookup on recipes by image_url or cuisine if frequently queried
CREATE INDEX IF NOT EXISTS idx_recipes_cuisine ON recipes (cuisine);
CREATE INDEX IF NOT EXISTS idx_recipes_meal_time ON recipes (time_mins); -- If you plan to filter by time

-- Optional: Create an index on user_feedback for faster lookup by user_id
CREATE INDEX IF NOT EXISTS idx_user_feedback_user_id ON user_feedback (user_id);