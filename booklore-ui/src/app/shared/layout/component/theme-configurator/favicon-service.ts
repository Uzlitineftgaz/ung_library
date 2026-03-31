import {Injectable} from '@angular/core';

@Injectable({providedIn: 'root'})
export class FaviconService {
  updateFavicon(_color: string) {
    let favicon = document.querySelector("link[rel*='icon']") as HTMLLinkElement;
    if (!favicon) {
      favicon = document.createElement('link');
      favicon.rel = 'icon';
      document.head.appendChild(favicon);
    }

    favicon.type = 'image/png';
    favicon.href = 'assets/favicon.png';
  }
}
