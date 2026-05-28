const PROTOTYPE_THEME_STYLE_ID = "records-ai-prototype-theme";

export function loadPrototypeTheme() {
  if (typeof document === "undefined") return;
  if (document.getElementById(PROTOTYPE_THEME_STYLE_ID)) return;

  const style = document.createElement("style");
  style.id = PROTOTYPE_THEME_STYLE_ID;
  style.textContent = `
    :root {
      --paper: 42 46% 96%;
      --navy: 211 48% 22%;
      --gold: 41 78% 47%;
    }

    .font-mono {
      font-family: "JetBrains Mono", "SFMono-Regular", Consolas, "Liberation Mono", monospace;
    }
  `;
  document.head.appendChild(style);
}

loadPrototypeTheme();
