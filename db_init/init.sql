-- init.sql
-- This script will be executed by Docker Compose when the MariaDB container starts for the first time.
-- It sets up the database schema for the AI-powered food app.

-- Create the main database
CREATE DATABASE IF NOT EXISTS foodapp;
USE foodapp;

-- 1. Recipes Table
-- Stores all the recipe information from the JSON dataset.
-- 'id' will be a unique identifier for each recipe.
-- JSON types are used for 'ingredients', 'instructions', and 'keywords' to store
-- structured array data that will be processed by the ML backend.
CREATE TABLE IF NOT EXISTS recipes (
    id VARCHAR(255) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    recipe_url TEXT,
    image_url TEXT,
    ingredients JSON, -- Stores an array of all the ingredients used in the recipe
    instructions JSON, -- Stores an array of instruction steps
    category VARCHAR(100),
    cuisine VARCHAR(100),
    site_name VARCHAR(100),
    keywords JSON, -- Stores an array of keywords/tags
    dietary_restrictions JSON, -- Stores dietary restrictions if any
    total_time INT, -- Total time in minutes
    overall_rating DECIMAL(3,2) -- Rating from 0.0 to 5.0
);

-- 2. Users Table
-- Stores user information from OAuth providers (Google, etc.)
-- 'id' is the unique identifier from the OAuth provider
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(255) PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    image_url TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_email (email)
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

-- 4. User Saved Recipes Table
-- Stores recipes that users have saved for later reference.
-- A composite primary key ensures a user can only save a recipe once.
CREATE TABLE IF NOT EXISTS user_saved_recipes (
    user_id VARCHAR(255) NOT NULL,
    recipe_id VARCHAR(255) NOT NULL,
    saved_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, recipe_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
);

-- 5. Recommendations Table
-- Stores pre-calculated recommendations for each user. The ML API will update this table.
-- A composite primary key ensures a user can only have one recommendation entry per recipe.
-- An auto-incrementing index ensures proper ordering of recommendations for each user.
CREATE TABLE IF NOT EXISTS recommendations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    recipe_id VARCHAR(255) NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_user_recipe (user_id, recipe_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
);

-- Create an index on user_feedback for faster lookup by user_id
CREATE INDEX IF NOT EXISTS idx_user_feedback_user_id ON user_feedback (user_id);

-- Create an index on recommendations for faster lookup by user_id
CREATE INDEX IF NOT EXISTS idx_recommendations_user_id ON recommendations (user_id);

-- Create an index on user_saved_recipes for faster lookup by user_id
CREATE INDEX IF NOT EXISTS idx_user_saved_recipes_user_id ON user_saved_recipes (user_id);

-- Create indexes for users table
CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users (created_at);