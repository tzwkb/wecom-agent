import { defineConfig, markdown } from "sourcey";

const canonicalUrl = new URL(
  process.env.READTHEDOCS_CANONICAL_URL ??
    "https://wecom-agent.readthedocs.io/en/latest/",
);

export default defineConfig({
  name: "WeCom Agent",
  siteUrl: canonicalUrl.origin,
  baseUrl: canonicalUrl.pathname,
  repo: "https://github.com/tzwkb/wecom-agent",
  editBranch: "main",
  editBasePath: "docs",
  theme: {
    preset: "default",
    colors: {
      primary: "#07C160",
      light: "#2DCB71",
      dark: "#056B38",
    },
    fonts: {
      sans: "Inter, ui-sans-serif, system-ui, sans-serif",
      mono: "ui-monospace, SFMono-Regular, Menlo, monospace",
    },
    layout: {
      sidebar: "17rem",
      toc: "18rem",
      content: "48rem",
    },
  },
  navigation: {
    tabs: [
      {
        tab: "Documentation",
        slug: "",
        source: markdown({
          groups: [
            {
              group: "Start Here",
              pages: ["introduction", "quickstart"],
            },
            {
              group: "Workflows",
              pages: [
                "local-reading",
                "online-documents",
                "online-sheets",
                "smart-sheets",
                "mcp-tools",
              ],
            },
            {
              group: "Reference",
              pages: ["security", "api-reference", "troubleshooting"],
            },
          ],
        }),
      },
    ],
  },
});
