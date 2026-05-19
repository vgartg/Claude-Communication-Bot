export interface Health {
  status: string;
  version: string;
  pending_asks: number;
}

export interface RouteCatalogEntry {
  id: string;
  method: string;
  path: string;
  description: string;
  auth: boolean;
}

export interface PendingItem {
  ask_id: string;
  question: string;
  options: string[];
  session_id: string | null;
}

export interface PendingList {
  items: PendingItem[];
}
