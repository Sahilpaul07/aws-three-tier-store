# aws-three-tier-store
AWS Three-Tier Store using EC2, ALB, Flask and RDS MySQL
# AWS Three-Tier Store Application

## Project Overview

This project is a web-based shopping store built using AWS infrastructure, Python Flask, and MySQL. Users can view products, add items to a shopping cart, proceed to checkout, and place orders.

## Architecture

User Browser → Application Load Balancer → Amazon EC2 (Flask Application) → Amazon RDS (MySQL)

## AWS Services Used

- **Amazon VPC:** Isolated network for the application infrastructure.
- **Amazon EC2:** Hosts the Flask application.
- **Application Load Balancer:** Routes HTTP requests to the application server.
- **Amazon RDS for MySQL:** Stores products, orders, and order items.
- **Security Groups:** Control inbound and outbound network traffic.
- **EC2 Instance Connect Endpoint:** Enables access to the private EC2 instance.

## Technologies Used

- Python
- Flask
- Gunicorn
- PyMySQL
- MySQL
- HTML and CSS
- Linux / Amazon Linux

## Application Features

- Product listing from MySQL database
- Add to Cart functionality
- Shopping cart and checkout
- Customer order processing
- Order and order-item storage
- Inventory stock reduction after an order
- Health endpoint for application checks

## Database Structure

### products
Stores product ID, name, description, price, stock, and creation timestamp.

### orders
Stores order ID, customer name, customer email, total amount, status, and creation timestamp.

### order_items
Stores item ID, order ID, product ID, quantity, and unit price.

## Testing and Validation

- Verified that the application homepage loads.
- Tested the shopping cart and checkout flow.
- Confirmed that orders are stored in MySQL.
- Confirmed that order items are stored correctly.
- Verified inventory reduction after an order.

## Learning Outcomes

- AWS VPC and security group configuration
- Load balancing with an Application Load Balancer
- Deploying a Flask application on EC2
- Connecting an application to RDS MySQL
- Database queries and relational table design
- Troubleshooting application and network connectivity

## Future Improvements

- Add payment gateway integration.
- Add user authentication.
- Deploy multiple application instances across Availability Zones.
- Configure HTTPS using a domain and TLS certificate.
- Add monitoring and alerting with Amazon CloudWatch.

## Disclaimer

This is a learning project. Orders are test orders; no real payment processing is implemented.

