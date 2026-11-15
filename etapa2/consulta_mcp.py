"""Compara a mesma pergunta ao mesmo modelo (qwen2.5:7b via Bedrock do Floci) sem e com o AWS Documentation MCP Server.

Uso: python consulta_mcp.py
O cliente MCP sobe o servidor por stdio (uvx), como Kiro/VS Code fariam, busca na documentação oficial e entrega os
trechos ao modelo como contexto (RAG). Saídas: sem-mcp.txt, com-mcp.txt e contexto-mcp.txt.
"""
import asyncio, os

import boto3
from botocore.config import Config
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

AQUI = os.path.dirname(os.path.abspath(__file__))
PERGUNTA = ("Explique a diferença entre Security Group e Network ACL (NACL) na AWS: nível em que atuam, se são stateful ou "
            "stateless, tipos de regra (allow/deny), ordem de avaliação e quantos podem ser associados. "
            "Cite as páginas da documentação usadas, se houver.")
bedrock = boto3.client("bedrock-runtime", config=Config(read_timeout=300, retries={"max_attempts": 1}))


def perguntar(texto):
    r = bedrock.converse(modelId="anthropic.claude-3-haiku-20240307-v1:0",
                         messages=[{"role": "user", "content": [{"text": texto}]}],
                         inferenceConfig={"maxTokens": 1200, "temperature": 0})
    return r["output"]["message"]["content"][0]["text"]


def texto_de(resultado):
    return "\n".join(c.text for c in resultado.content if getattr(c, "text", None))


async def buscar_documentacao():
    servidor = StdioServerParameters(
        command="uvx", args=["awslabs.aws-documentation-mcp-server@latest"],
        env={**os.environ, "FASTMCP_LOG_LEVEL": "ERROR", "AWS_DOCUMENTATION_PARTITION": "aws"})
    async with stdio_client(servidor) as (leitura, escrita), ClientSession(leitura, escrita) as sessao:
        await sessao.initialize()
        ferramentas = [t.name for t in (await sessao.list_tools()).tools]
        print("ferramentas do servidor MCP:", ferramentas)
        busca = await sessao.call_tool("search_documentation",
                                       {"search_phrase": "compare security groups and network ACLs", "limit": 5})
        print("search_documentation →\n", texto_de(busca)[:1500])
        url = "https://docs.aws.amazon.com/vpc/latest/userguide/infrastructure-security.html"
        for linha in texto_de(busca).splitlines():  # usa a primeira URL da VPC que a busca devolver
            if "docs.aws.amazon.com/vpc/" in linha:
                url = linha[linha.index("https://"):].split()[0].strip('",)')
                break
        pagina = await sessao.call_tool("read_documentation", {"url": url, "max_length": 6000})
        print("read_documentation →", url)
        return f"Fonte: {url}\n\n{texto_de(pagina)}"


def main():
    sem = perguntar(PERGUNTA)
    open(os.path.join(AQUI, "sem-mcp.txt"), "w").write(sem)
    contexto = asyncio.run(buscar_documentacao())
    open(os.path.join(AQUI, "contexto-mcp.txt"), "w").write(contexto)
    com = perguntar(f"Use a documentação oficial abaixo para responder.\n<documentacao>\n{contexto}\n</documentacao>\n\n{PERGUNTA}")
    open(os.path.join(AQUI, "com-mcp.txt"), "w").write(com)
    print("\n===== SEM MCP =====\n", sem, "\n\n===== COM MCP =====\n", com)


if __name__ == "__main__":
    main()
