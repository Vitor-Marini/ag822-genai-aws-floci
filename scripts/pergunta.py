"""Pergunta ao "Bedrock" do Floci (qwen2.5:7b local). Uso: python scripts/pergunta.py arquivo_prompt.txt [contexto.txt]"""
import boto3, sys
from botocore.config import Config

prompt = open(sys.argv[1]).read()
if len(sys.argv) > 2:  # contexto opcional (ex.: trechos da documentação vindos do MCP)
    prompt = f"Use a documentação abaixo para responder.\n<documentacao>\n{open(sys.argv[2]).read()}\n</documentacao>\n\n{prompt}"
resp = boto3.client("bedrock-runtime", config=Config(read_timeout=300, retries={"max_attempts": 1})).converse(
    modelId="anthropic.claude-3-haiku-20240307-v1:0",
    messages=[{"role": "user", "content": [{"text": prompt}]}],
    inferenceConfig={"maxTokens": 3000, "temperature": 0},
)
print(resp["output"]["message"]["content"][0]["text"])
