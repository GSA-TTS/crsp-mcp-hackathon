---
title: "Inline micro form MCP App"
description: "Setup, architecture, and validation guide for the USWDS-styled MCP App prototype"
status: draft
tier: 3
last_updated: "2026-10-30"
---

# Inline micro form MCP App

This repository is a small [MCP Apps](https://github.com/modelcontextprotocol/ext-apps/blob/main/specification/2026-01-26/apps.mdx) prototype for testing an interactive form *inside* an MCP-compatible chat client. The form has a USWDS-styled task-name input and Low, Medium, and High priority buttons. Medium is selected initially; clicking a button changes the selected style and an on-screen status message. **The task name and priority are never submitted or saved.** Clients that cannot show the app receive a plain-text tool result instead.

## Requirements and setup

- Node.js 20 or later and npm
- An MCP host with MCP Apps support to see the inline UI (Goose Desktop is one option)

From the repository directory:

```sh
npm ci
npm run check
```

`npm ci` installs the exact versions in `package-lock.json`. `npm run check` runs JavaScript syntax checks, tests, and `npm audit --omit=dev` (which needs access to the npm registry). There is no separate build or lint command. `npm start` starts the stdio MCP server; run it through an MCP host rather than expecting a browser page or a listening port.

## Try it in Goose Desktop

1. Complete setup above. In Goose Desktop, open **Extensions → Add custom extension**, select **Standard IO**, set ID to `inline-micro-form`, and use `node /absolute/path/to/this-repo/server.js` as the command. Replace the example path with the absolute path to this repository's `server.js`.
2. Restart Goose Desktop to load the extension. Ask it to **"Call show_micro_form from inline-micro-form"**. The tool takes no arguments.
3. Look for the task-name field and three priority buttons *inside the chat*. Click Low or High: its selected appearance and the status message should change. The status should remain visible rather than being clipped by a small frame.

If only the fallback sentence appears, the tool is missing, or the frame is clipped, restart Goose and call the tool again. Record the Goose version and what you observed. Goose describes MCP Apps support as experimental; passing automated tests does **not** establish live rendering in a particular host. OpenChamber inline rendering has not been confirmed; configure the same stdio server there if it supports MCP Apps and perform the same manual check.

## How it works

| File | Purpose |
| --- | --- |
| `server.js` | Exposes the `show_micro_form` tool and its `ui://inline-micro-form/main` HTML resource over stdio. |
| `view.html` | Inline form, priority selection, host initialization, and frame-size notifications. |
| `server.test.js` | Tests MCP tool/resource wiring, embedded styles, selection behavior, and size notifications. |
| `package.json`, `package-lock.json` | Pinned dependencies and npm commands. |
| `docs/decisions/0001-use-mcp-apps-for-inline-rendering.md` | Proposed rationale for using MCP Apps. |

The tool links to the UI resource in its metadata and returns a readable text fallback. The server embeds only the needed CSS rules from the installed, pinned `@uswds/uswds` package into the HTML it serves. It uses local font fallbacks rather than USWDS font or icon assets; the view makes no external asset requests and its resource metadata declares no permitted network domains. The view initializes with the host and requests a content-based height of at least 400 CSS pixels to help avoid clipping in Goose.

## Verification and limitations

`npm test` exercises the stdio MCP protocol and UI script behavior without launching a graphical host. Use `npm run check` for the repository's full automated check. For an end-to-end check, follow the Goose steps above and inspect the actual inline result; automated tests alone cannot confirm host compatibility or accessibility in a real client.

This is an **inline rendering experiment**, not a task-management service. There is no form submission, persistence, authentication, or deployment configuration. Review AI-generated code before deploying it. For protocol context, see the [MCP Apps specification](https://github.com/modelcontextprotocol/ext-apps/blob/main/specification/2026-01-26/apps.mdx) and [Goose Desktop tutorial](https://github.com/aaif-goose/goose/blob/main/documentation/docs/tutorials/building-mcp-apps.md).
