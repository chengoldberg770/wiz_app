# Python API Application with Automated Deployment and Teardown

This project implements a simple Python API application that is containerized using Docker and deployed to AWS EC2 using Terraform.

## Project Structure

```
.
├── app.py                  # Python API application using FastAPI
├── requirements.txt        # Python dependencies
├── Dockerfile              # Docker configuration for containerization
├── main.tf                 # Main Terraform configuration
├── variables.tf            # Terraform variables definition
├── terraform.tfvars        # Example Terraform variables configuration
└── README.md               # This documentation file
```

## Prerequisites

- [Python 3.8+](https://www.python.org/downloads/)
- [Docker](https://docs.docker.com/get-docker/)
- [AWS CLI](https://aws.amazon.com/cli/) installed and configured with appropriate permissions
- [Terraform](https://www.terraform.io/downloads.html) (v1.0.0+)
- An AWS EC2 key pair for SSH access
- AWS account with necessary permissions for EC2, VPC, and security groups

## Python API Application

The application is built using FastAPI and provides the following endpoints:

- **GET /status**: Returns the current state of a shared variable (counter and message) along with metadata (timestamp and uptime).
- **POST /update**: Updates the shared variable and requires API key authentication.
- **GET /logs**: Returns a paginated list of all updates made to the shared variable.
- **GET /health**: Simple health check endpoint.

The application uses SQLite for persistent storage of the state and logs.

### API Key Authentication

The application implements API key authentication for the `/update` endpoint. The API key is set to `wiz` by default. In a production environment, this would be securely stored and retrieved from environment variables or a secrets manager.

To use the API key, include the header `API-Key: wiz` in your requests to the `/update` endpoint.

## Docker Setup

The Dockerfile uses multi-stage builds to optimize the image size:
1. The first stage installs dependencies and creates wheels
2. The second stage copies only the necessary files and wheels to create a lightweight image
3. The application runs as a non-root user for security

## Deployment with Terraform

### Setup

1. Clone this repository:
   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```

2. Create a `terraform.tfvars` file based on the example:
   ```bash
   cp terraform.tfvars terraform.tfvars
   ```

3. Edit `terraform.tfvars` with your AWS region, EC2 key pair name, and local path to your private key file.

### Deployment

1. Initialize Terraform:
   ```bash
   terraform init
   ```

2. Plan the deployment:
   ```bash
   terraform plan
   ```

3. Apply the Terraform configuration:
   ```bash
   terraform apply
   ```

4. After the deployment completes, Terraform will output:
   - The public IP address of the EC2 instance
   - SSH command to connect to the instance
   - URLs for the API endpoints

### Verification

Use the API endpoints provided in the Terraform output to verify the functionality:

1. Check the initial state:
   ```bash
   curl http://<public-ip>:5000/status
   ```

2. Update the state:
   ```bash
   curl -X POST http://<public-ip>:5000/update \
     -H "Content-Type: application/json" \
     -H "API-Key: wiz" \
     -d '{"counter": 42, "message": "Updated state"}'
   ```

3. Verify the updated state:
   ```bash
   curl http://<public-ip>:5000/status
   ```

4. Check the logs:
   ```bash
   curl http://<public-ip>:5000/logs
   ```

### Teardown

To destroy all resources created by Terraform:

```bash
terraform destroy
```

This will remove the EC2 instance and the security group created during deployment.

## Design Decisions and Trade-offs

### Python API Application
- **FastAPI** was chosen for its performance, built-in validation, and automatic documentation generation.
- **SQLite** was used for persistence as it's lightweight and requires no additional server setup, making it ideal for this demonstration. In a production environment, a more robust database might be preferable.
- The application stores logs of all state changes, providing an audit trail of updates.

### Docker
- **Multi-stage builds** were implemented to reduce the final image size by excluding build tools and intermediate files.
- A **non-root user** runs the application for enhanced security.
- **Volume mounting** is used to persist the SQLite database outside the container.

### Terraform
- **User data script** is used to set up the EC2 instance, install Docker, and deploy the application. In a production environment, a more sophisticated approach such as Ansible or AWS Systems Manager might be preferred.
- **Security group** is configured to only allow access from the IP address of the machine running the Terraform script, enhancing security.
- **Outputs** provide easy access to important information such as the instance IP and API endpoints.

### Security Considerations
- API key authentication is implemented for the update endpoint.
- The security group restricts access to only the IP running the Terraform script.
- The application runs as a non-root user in Docker.
- In a production environment, additional security measures would be recommended:
  - HTTPS/TLS encryption
  - More robust authentication (OAuth, JWT)
  - Secrets management (AWS Secrets Manager, HashiCorp Vault)
  - Enhanced logging and monitoring

## Future Improvements
- Add automated testing
- Implement CI/CD pipeline
- Add HTTPS support with Let's Encrypt
- Implement more robust authentication and authorization
- Use AWS RDS or DynamoDB instead of SQLite for better scalability
- Implement monitoring and alerting
