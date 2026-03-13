FROM php:8.1-apache

# Install mysqli extension
RUN docker-php-ext-install mysqli && docker-php-ext-enable mysqli

# Enable Apache mod_rewrite
RUN a2enmod rewrite

# Set working directory
WORKDIR /var/www/html

# Copy frontend to root
COPY ./web_ui/ /var/www/html/

# Copy API backend to /api/
COPY ./backend/php/ /var/www/html/api/

# Set permissions
RUN chown -R www-data:www-data /var/www/html
