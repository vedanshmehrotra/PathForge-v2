"""LeetCode GraphQL client — cache-miss problem metadata fetcher only.

Runtime analysis must never call this module.
Only ProblemResolver may invoke this.
"""

import json
import re
import urllib.error
import urllib.request
from typing import Optional


LEETCODE_GRAPHQL_URL = "https://leetcode.com/graphql"
REQUEST_TIMEOUT = 15


class GraphQLUnavailableError(Exception):
    """Raised when the LeetCode GraphQL API is unreachable or returns transport errors."""


_QUESTION_QUERY = """
query problemData($titleSlug: String!) {
  question(titleSlug: $titleSlug) {
    questionId
    title
    titleSlug
    content
    difficulty
    topicTags { name slug }
    exampleTestcases
    hints
  }
}
"""

_LIST_QUERY = """
query problemsetQuestionList($categorySlug: String, $limit: Int, $filters: QuestionListFilterInput) {
  problemsetQuestionList: questionList(
    categorySlug: $categorySlug
    limit: $limit
    filters: $filters
  ) {
    questions: data {
      questionFrontendId
      titleSlug
    }
  }
}
"""


def _post_graphql(query: str, variables: dict) -> Optional[dict]:
    data = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Referer": "https://leetcode.com/",
        "Origin": "https://leetcode.com",
    }
    req = urllib.request.Request(LEETCODE_GRAPHQL_URL, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            return json.loads(resp.read())
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
        raise GraphQLUnavailableError(
            f"LeetCode GraphQL API unreachable: {exc}"
        ) from exc
    except json.JSONDecodeError:
        return None


def fetch_problem_by_slug(title_slug: str) -> Optional[dict]:
    """Fetch full problem metadata from LeetCode GraphQL API by title slug.

    Returns a dict with keys: questionId, title, titleSlug, content,
    difficulty, topicTags, exampleTestcases, hints.
    Returns None if the request fails or the slug is unknown.
    """
    result = _post_graphql(_QUESTION_QUERY, {"titleSlug": title_slug})
    if result is None:
        return None
    question = result.get("data", {}).get("question")
    if not question or not question.get("questionId"):
        return None
    return question


def fetch_title_slug_by_id(question_id: int) -> Optional[str]:
    """Resolve a numeric LeetCode problem number (questionFrontendId) to its title slug.

    Uses the problemset questionList search API to find the problem by its
    public frontend ID. Example: 1 -> 'two-sum'
    Returns None if resolution fails.
    """
    search_term = str(question_id)
    filters = {"searchKeywords": search_term}
    result = _post_graphql(
        _LIST_QUERY,
        {"categorySlug": "", "limit": 15, "filters": filters},
    )
    if result is None:
        return None
    data = result.get("data")
    if not data:
        return None
    questions = data.get("problemsetQuestionList", {}).get("questions", [])
    for q in questions:
        if q.get("questionFrontendId") == search_term:
            return q.get("titleSlug")
    return None


def extract_title_slug_from_url(url: str) -> str:
    """Extract the title slug from a LeetCode URL.

    'https://leetcode.com/problems/two-sum/' -> 'two-sum'
    Returns empty string if the URL does not contain '/problems/'.
    """
    marker = "/problems/"
    idx = url.find(marker)
    if idx == -1:
        return ""
    slug = url[idx + len(marker):]
    slug = slug.rstrip("/").split("/")[0]
    return slug


def html_to_plain_text(html: str) -> str:
    """Strip HTML tags from a LeetCode problem description.

    Returns readable plain text. Also handles common HTML entities.
    """
    if not html:
        return ""
    text = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL)
    text = re.sub(r"<pre[^>]*>", "\n", text)
    text = re.sub(r"</pre>", "\n", text)
    text = re.sub(r"<br\s*/?>", "\n", text)
    text = re.sub(r"<li[^>]*>", "\n- ", text)
    text = re.sub(r"<code[^>]*>", "", text)
    text = re.sub(r"</code>", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()
