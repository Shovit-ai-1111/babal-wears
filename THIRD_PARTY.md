# Third-party assets

Libraries and fonts are self-hosted; visitors do not need a CDN connection. Original upstream headers are retained in the JavaScript files.

| Asset | Version/source | License |
| --- | --- | --- |
| GSAP | 3.13.0, npm `gsap`, `dist/gsap.min.js` | GreenSock standard no-charge license, https://gsap.com/standard-license |
| HTMX | 2.0.4, npm `htmx.org`, `dist/htmx.min.js` | BSD 2-Clause; bundled `htmx-LICENSE.txt` |
| Alpine | 3.14.9, npm `alpinejs`, `dist/cdn.min.js` | MIT; bundled `alpine-LICENSE.txt` |
| Inter variable Latin | Fontsource Inter variable, https://rsms.me/inter/ | SIL OFL 1.1; bundled `inter-OFL.txt` |
| Noto Sans Devanagari variable | Fontsource, https://github.com/notofonts/devanagari | SIL OFL 1.1; bundled `noto-OFL.txt` |
| DejaVu Sans Bold | Runtime system package `fonts-dejavu-core`, used only to rasterize demo art | DejaVu/Bitstream notices supplied by the system package |

The GSAP upstream README is bundled as `gsap-README.md` and links its license. This project uses GSAP core only; it implements rail momentum with pointer velocity and core tweens, without an extra paid/inertia plugin dependency. Refer to each upstream license when redistributing third-party assets.

The T-shirt SVG, geometric band, favicon, demo print compositions and product illustrations are original code-generated placeholders made for this project. They are not extracted from Instagram or represented as official BABAL WEARS artwork.
