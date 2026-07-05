import { track, useEditor } from "tldraw";
import { pageIdForSlug } from "../../actions/seedTldrawDocument";
import { PAGES } from "../../lib/pages";

export const PageTabs = track(function PageTabs() {
  const editor = useEditor();
  const currentPageId = editor.getCurrentPageId();

  return (
    <nav className="page-tabs" aria-label="Workshop pages">
      {PAGES.map((page) => {
        const pageId = pageIdForSlug(page.slug);
        const isActive = pageId === currentPageId;
        return (
          <button
            key={page.slug}
            type="button"
            data-testid={`page-tab-${page.slug}`}
            className={isActive ? "page-tab page-tab-active" : "page-tab"}
            onClick={() => editor.setCurrentPage(pageId)}
          >
            {page.title}
          </button>
        );
      })}
    </nav>
  );
});
