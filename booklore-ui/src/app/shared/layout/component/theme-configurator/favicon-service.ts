import {Injectable} from '@angular/core';

@Injectable({providedIn: 'root'})
export class FaviconService {
  private svgTemplate = () => `
         <img
                ngSrc="assets/icon.png"
                class="logo-icon"
                alt="logo"
                height="1024" width="1024"
              />
  `;

  updateFavicon(color: string) {
    // const svg = this.svgTemplate(color);
    const svg = this.svgTemplate();
    // const blob = new Blob([svg], {type: 'image/svg+xml'});
    const blob = new Blob([svg], {type: 'image/png'});
    const url = URL.createObjectURL(blob);

    let favicon = document.querySelector("link[rel*='icon']") as HTMLLinkElement;
    if (!favicon) {
      favicon = document.createElement('link');
      favicon.rel = 'icon';
      document.head.appendChild(favicon);
    }

    // favicon.type = 'image/svg+xml';
    favicon.type = 'image/png';
    favicon.href = url;
  }
}
