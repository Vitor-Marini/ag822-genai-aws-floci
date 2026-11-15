```bash
#!/bin/bash

# Título da seção S3
echo "Buckets S3 na sua conta AWS:"
aws s3api list-buckets --query "Buckets[].Name" --output text

# Título da seção DynamoDB
echo "Tabelas DynamoDB na sua conta AWS:"
aws dynamodb list-tables --query "TableNames" --output text

# Título da seção IAM
echo "Usuários IAM na sua conta AWS:"
aws iam list-users --query "Users[].UserName" --output text
```
Salve este script em um arquivo, por exemplo `aws_info.sh`, dê permissão de execução com `chmod +x aws_info.sh` e execute-o com `./aws_info.sh`. Certifique-se de que suas credenciais AWS estejam configuradas corretamente no ambiente onde este script será executado.
