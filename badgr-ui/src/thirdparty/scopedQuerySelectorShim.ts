/* scopeQuerySelectorShim.js
*
* Copyright (C) 2015 Larry Davis
* All rights reserved.
*
* This software may be modified and distributed under the terms
* of the BSD license.  See the LICENSE file for details.
*/
(() => {
    if (!HTMLElement.prototype.querySelectorAll) {
        throw new Error("rootedQuerySelectorAll: This polyfill can only be used with browsers that support querySelectorAll");
    }

    // Badgr Note: This function was moved out of the catch statement to avoid this strict-mode error in safari:
    // SyntaxError: Strict mode does not allow function declarations in a lexically nested statement.

    // Match usage of scope
    const scopeRE = /^\s*:scope/gi;
    // Overrides
    function overrideNodeMethod(prototype, methodName) {
        // Store the old method for use later
        const oldMethod = prototype[methodName];
        // Override the method
        prototype[methodName] = function(query) {
            let nodeList, gaveId = false, gaveContainer = false;
            if (query.match(scopeRE)) {
                // Remove :scope
                query = query.replace(scopeRE, "");
                if (!this.parentNode) {
                    // Add to temporary container
                    container.appendChild(this);
                    gaveContainer = true;
                }
                const parentNode = this.parentNode;
                if (!this.id) {
                    // Give temporary ID
                    this.id = "rootedQuerySelector_id_" + new Date().getTime();
                    gaveId = true;
                }
                // Find elements against parent node
                nodeList = oldMethod.call(parentNode, "#" + this.id + " " + query);
                // Reset the ID
                if (gaveId) {
                    this.id = "";
                }
                // Remove from temporary container
                if (gaveContainer) {
                    container.removeChild(this);
                }
                return nodeList;
            } else {
                // No immediate child selector used
                return oldMethod.call(this, query);
            }
        };
    }

    // A temporary element to query against for elements not currently in the DOM
    // We'll also use this element to test for :scope support
    const container = document.createElement("div");
    // Check if the browser supports :scope
    try {
        // Browser supports :scope, do nothing
        container.querySelectorAll(":scope *");
    } catch (e) {
        // Browser doesn't support :scope, add polyfill
        overrideNodeMethod(HTMLElement.prototype, "querySelector");
        overrideNodeMethod(HTMLElement.prototype, "querySelectorAll");
    }
})();
