# Three-Tier Store on AWS --- Project Documentation

## 1. Project Overview

This project is a simple online store hosted on AWS. It demonstrates a
three-tier architecture:

1.  **Presentation tier:** Users access the store through a web browser
    and the Application Load Balancer (ALB).
2.  **Application tier:** A Flask application runs on a private EC2
    instance and handles products, cart, and checkout.
3.  **Database tier:** Amazon RDS for MySQL stores product and order
    data.

**AWS Region:** `us-east-1` (N. Virginia)

> This document describes the project setup and observed tests. Verify
> the current AWS console state before presenting the architecture as
> fully production-ready.

## 2. Architecture

``` text
User / Browser
      |
      v
Application Load Balancer (HTTP :80)
      |
      v
Target Group (HTTP :5000)
      |
      v
Private EC2 App Server (Flask + Gunicorn)
      |
      v
Amazon RDS for MySQL (appdb)
```

The VPC is `ThreeTier-VPC` with CIDR `10.0.0.0/16` and six subnets.

## 3. AWS Services Used

  -----------------------------------------------------------------------
  Service                             Purpose
  ----------------------------------- -----------------------------------
  Amazon VPC                          Isolated network for the project

  Subnets                             Separate network segments for the
                                      tiers and availability zones

  Security Groups                     Control inbound and outbound
                                      traffic

  Application Load Balancer           Receives web traffic and forwards
                                      it to the application target

  EC2                                 Hosts the Flask application

  Target Group                        Routes ALB traffic to the
                                      application on port 5000 and checks
                                      health

  Amazon RDS for MySQL                Stores products and orders

  IAM Role                            Provides the EC2 instance with AWS
                                      permissions

  Instance Connect Endpoint           Allows connection to the private
                                      EC2 instance

  systemd                             Runs the application service

  Flask                               Web application framework

  Gunicorn                            Runs the Flask app as a WSGI server

  PyMySQL                             Connects the Python app to MySQL
  -----------------------------------------------------------------------

## 4. Main AWS Resources

-   **VPC:** `ThreeTier-VPC`
-   **VPC ID:** `vpc-082a45658cf7d5d4d`
-   **VPC CIDR:** `10.0.0.0/16`
-   **Application Load Balancer:** `ThreeTier-ALB`
-   **Target Group:** `App-TG`
-   **App EC2 instance:** `App-Server-A`
-   **App instance ID:** `i-0f3d5eaa7686bfbe7`
-   **App private IP:** `10.0.11.17`
-   **RDS database name:** `appdb`
-   **RDS endpoint:**
    `threetier-mysql-db.c632i8g0yd8g.us-east-1.rds.amazonaws.com`

Do not publish passwords, secret keys, `.env` files, or other
credentials in this repository.

## 5. Application Features

The store was tested with these products:

-   Wireless Mouse --- ₹599
-   Mechanical Keyboard --- ₹1,999
-   USB-C Hub --- ₹1,299

Observed functionality: - Product list displayed in the browser. -
Add-to-cart functionality worked. - Checkout completed and showed an
order confirmation. - An order record and related order-item records
were visible in MySQL. - Product stock changed after an order was
placed.

## 6. Application Setup on EC2

The application directory is:

``` bash
/home/ec2-user/app
```

Useful commands for inspecting the application and service:

``` bash
cd /home/ec2-user/app
ls -la
cat requirements.txt
sudo systemctl status three-tier-app
sudo journalctl -u three-tier-app -n 100 --no-pager
```

Restart the service after a legitimate application or configuration
change:

``` bash
sudo systemctl restart three-tier-app
```

The service configuration uses:

``` ini
[Service]
WorkingDirectory=/home/ec2-user/app
EnvironmentFile=/etc/three-tier-app.env
ExecStart=/home/ec2-user/.local/bin/gunicorn --workers 2 --bind 0.0.0.0:5000 --access-logfile - --error-logfile - app:app
```

The environment file contains database connection settings and a Flask
secret key. Keep it on the server and **never commit it to GitHub**.

## 7. Database

The database name is `appdb`. The application uses MySQL tables for
products, orders, and order items.

-   `products`: product details, price, and stock.
-   `orders`: customer/order details, total, and order status.
-   `order_items`: products and quantities associated with each order.

A local shell helper named `db` was configured in `~/.bashrc` to
simplify database queries in the EC2 session. That helper is specific to
the server and is not required by GitHub users.

## 8. Security Group Flow

The intended traffic flow is:

-   Internet users access the ALB over HTTP port 80.
-   The ALB forwards requests to the app target on TCP port 5000.
-   `App-SG` permits TCP port 5000 from `ALB-SG`.
-   The app connects to RDS on the MySQL port, normally TCP 3306, with
    the database security group restricted to the app tier.

Check the current RDS security group rules in the AWS console to confirm
that access is limited to the application security group.

## 9. Health Checks and Troubleshooting

The target group `App-TG` uses an HTTP health check on path `/` and
traffic port 5000. During setup, the target was observed as unhealthy at
one point, so check its current status before demos or interviews.

Useful checks:

``` bash
sudo systemctl status three-tier-app
sudo journalctl -u three-tier-app -n 100 --no-pager
curl -i http://127.0.0.1:5000/
```

If the target is unhealthy, check: 1. The app service is running. 2. The
application responds successfully on `/`. 3. The app security group
permits port 5000 from the ALB security group. 4. The target group uses
the correct port and health-check path. 5. Database connection errors
are not preventing the app from responding.

## 10. GitHub Repository Contents

Suggested repository files:

``` text
aws-three-tier-store/
├── README.md
├── PROJECT-DOCUMENTATION.md
├── app.py
├── requirements.txt
└── screenshots/
    └── README.md
```

The `screenshots/` folder can contain non-sensitive project screenshots
when available. Do not include secrets or customer data.

## 11. Cost and Cleanup Notes

AWS resources may incur charges even when the application is not
actively being used. Review the billing dashboard and delete resources
you no longer need, including load balancers, EC2 instances, RDS
databases, NAT gateways, and unused public IPv4 addresses. Take care not
to delete resources you still need.

## 12. Interview Explanation

"I built a three-tier store project on AWS. I created a VPC with subnets
and security groups, deployed a Flask application on an EC2 instance,
and placed an Application Load Balancer in front of the app. The
application connects to an Amazon RDS MySQL database to store products
and orders. I used Gunicorn and systemd to run the app and tested
product browsing, adding items to the cart, and checkout. I also worked
with target-group health checks and security-group rules while
troubleshooting."

## 13. Before Publishing

-   [ ] Confirm the app code in GitHub matches the working server
    version.
-   [ ] Confirm `requirements.txt` includes the dependencies actually
    used.
-   [ ] Remove passwords, secret keys, `.env` files, and database
    credentials.
-   [ ] Confirm target-group health before claiming the deployment is
    healthy.
-   [ ] Add screenshots only after checking that they do not expose
    sensitive details.
