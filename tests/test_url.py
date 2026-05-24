from radar.utils.url import canonicalize_url


def test_canonicalize_url_removes_tracking_and_normalizes_https():
    url = canonicalize_url("http://Example.com/path/?utm_source=x&b=2&fbclid=abc#frag")
    assert url == "https://example.com/path?b=2"


def test_canonicalize_url_resolves_relative_links():
    assert canonicalize_url("/news/1/", "https://cs.nju.edu.cn/list") == "https://cs.nju.edu.cn/news/1"
