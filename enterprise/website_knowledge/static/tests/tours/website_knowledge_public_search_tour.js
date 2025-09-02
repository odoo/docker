/** @odoo-module */

/**
 * Public user search Knowledge flow tour (for published articles).
 * Features tested:
 * - Check that tree contains all articles
 * - Write search term in search bar
 * - Check that search tree renders the correct matching articles
 * - Clean search bar
 */

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('website_knowledge_public_search_tour', {
    steps: () => [{ // Check that section tree contains all articles
    content: "Check that search tree contains 'My Article'",
    trigger: '.o_article_name:contains("My Article")',
}, {
    content: "Unfold 'My Article'", // Unfold because 'My Article' wasn't added to the unfolded articles
    trigger: '.o_article_active .o_article_caret',
    run: "click",
}, {
    content: "Check that search tree contains 'Child Article'",
    trigger: '.o_article_name:contains("Child Article")',
}, { // Write search term in search bar
    content: "Write 'M' in the search bar",
    trigger: '.knowledge_search_bar',
    run: "edit My",
}, {
    content: "Trigger keyup event to start the search",
    trigger: '.knowledge_search_bar',
    run: "press Enter",
}, { // Check tree rendering with matching articles
    content: "Check that search tree contains 'My Article'",
    trigger: '.o_article_name:contains("My Article")',
}, {
    content: "Check that search tree doesn't contain 'Child Article'",
    trigger: '.o_knowledge_tree:not(:has(.o_article_name:contains("Child Article")))',
}, {
    content: "Check that search tree doesn't contain 'Sibling Article'",
    trigger: '.o_knowledge_tree:not(:has(.o_article_name:contains("Sibling Article")))',
}, { // Clean search bar
    content: "Clean search bar",
    trigger: '.knowledge_search_bar',
    run: "clear",
}]});
