provider "aws" {
  region = var.aws_region
}

# Get the current public IP address of the machine running Terraform
data "http" "my_public_ip" {
  url = "https://ifconfig.me/ip"
}

# Create a new Security Group
resource "aws_security_group" "app_sg" {
  name        = "api_app_sg"
  description = "Security group for the API application"

  # SSH access from the current IP
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["${chomp(data.http.my_public_ip.response_body)}/32"]
    description = "SSH access from Terraform machine"
  }

  # HTTP access for the API on port 5000 from the current IP
  ingress {
    from_port   = 5000
    to_port     = 5000
    protocol    = "tcp"
    cidr_blocks = ["${chomp(data.http.my_public_ip.response_body)}/32"]
    description = "API access from Terraform machine"
  }

  # Allow all outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

    tags = {
    Name = "api_app_security_group"
    }
}

# EC2 instance
resource "aws_instance" "app_instance" {
  ami             = var.ami_id # Amazon Linux 2 AMI
  instance_type   = "t2.micro"
  vpc_security_group_ids = [aws_security_group.app_sg.id]
  key_name        = var.key_name
  
  user_data       = <<-EOF
    #!/bin/bash
    set -e
    # Update system packages
    sudo yum update -y
    
    # Install Docker
    sudo yum install -y docker
    sudo systemctl start docker
    sudo systemctl enable docker
    sudo usermod -aG docker ec2-user
    
    # Install Git & Python
    sudo yum install -y git python3 python3-pip

    # Clone GitHub repo
    git clone https://github.com/chengoldberg770/wiz_app /home/ec2-user/api-app
    
    # Navigate to project directory
    cd /home/ec2-user/api-app
    
    # Install dependencies
    pip3 install -r requirements.txt
    
    # Build and run the Docker container
    sudo docker build -t api-app .
    sudo docker run -d -p 5000:5000 --name api-container api-app
  EOF

  tags = {
    Name = "api_app_instance"
  }
}

# Output the public IP of the EC2 instance
output "instance_public_ip" {
  value = aws_instance.app_instance.public_ip
  description = "The public IP address of the EC2 instance"
}

# Output SSH connection command
output "ssh_command" {
  value = "ssh -i ${var.key_path} ec2-user@${aws_instance.app_instance.public_ip}"
  description = "SSH command to connect to the EC2 instance"
}

# Output the API endpoints
output "api_status_endpoint" {
  value = "http://${aws_instance.app_instance.public_ip}:5000/status"
  description = "URL for the status endpoint"
}

output "api_update_endpoint" {
  value = "http://${aws_instance.app_instance.public_ip}:5000/update"
  description = "URL for the update endpoint"
}

output "api_logs_endpoint" {
  value = "http://${aws_instance.app_instance.public_ip}:5000/logs"
  description = "URL for the logs endpoint"
}
