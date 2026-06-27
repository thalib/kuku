class TestSmoke:
    def test_server_starts(self, page_goto):
        page = page_goto("/")
        assert "Kuku" in page.title()
