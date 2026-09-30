from django.shortcuts import render
from django.http import JsonResponse
import json
from django.views.decorators.csrf import csrf_exempt
from urllib.parse import urlparse
from .templates import REVIEW_TEMPLATES
import asyncio
from mcp_client import get_github_file,search_github_code
# Create your views here.

@csrf_exempt
def review_repo(request):
    if request.method !="POST":
        return JsonResponse(
            {
                "error":"Only POST method is allowed"
            },
            status=405
        )
    data =json.loads(request.body)
    

    github_url=data.get("github_url")
    template = data.get("template")

    def is_valid_github_url(url):
        try:
            parsed=urlparse(url)
            return(
                parsed.scheme=="https"
                and parsed.netloc=="github.com"
                and len(parsed.path.strip("/").split("/"))==2
            )
        except Exception:
            return False

    if not is_valid_github_url(github_url):
        return JsonResponse(
            {
                "error":"Invalid Github repository URL"
            },
            status=400
        )    

    VALID_TEMPLATES={
        "security",
        "code_quality",
        "scalability"
    }
    if template not in VALID_TEMPLATES:
        return JsonResponse(
            {
                "error":"Invalid template. Choose security,code_quality or scalability"
            },
            status=400
        )

    template_context=REVIEW_TEMPLATES[template]
    search_keywords=template_context["search_keywords"]
    print("SEARCH KEYWORDS:",search_keywords)

    def get_repo_details(url):
        parsed=urlparse(url)
        parts=parsed.path.strip("/").split("/")
        owner=parts[0]
        repo=parts[1]
        return owner,repo

    owner,repo=get_repo_details(github_url)
    print("OWNER:",owner,type(owner))
    print("REPO:",repo,type(repo))
    combined_query="token"
    result =asyncio.run(search_github_code(owner,repo,combined_query))
    print("SEARCH RESULT:",result)

    return JsonResponse(
        {
            "github_url":github_url,
            "template":template,
            "context":template_context,
            "github_result":result
        }
    )