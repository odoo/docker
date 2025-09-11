import { HtmlViewer } from "@html_editor/fields/html_viewer";

export class PublicHtmlViewer extends HtmlViewer {
    retargetLink(link) {
        const href = link?.getAttribute("href") || "";
        if (href.startsWith("/knowledge/article") || href.startsWith("/web/login")) {
            return;
        }
        super.retargetLink(link);
    }
}
