import {SortOption} from './sort.model';

export interface Shelf {
  id?: number;
  name: string;
  icon?: string | null;
  iconType?: 'PRIME_NG' | 'CUSTOM_SVG' | 'CUSTOM_IMAGE' | null;
  sort?: SortOption;
  publicShelf?: boolean;
  userId?: number;
  bookCount?: number;
}
