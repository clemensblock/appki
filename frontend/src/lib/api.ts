const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface NewsItem {
  id: number;
  title: string;
  url: string;
  summary: string | null;
  source: string | null;
  category: string | null;
  published_at: string | null;
  fetched_at: string | null;
  title_de: string | null;
  summary_de: string | null;
  enrichment_status: string | null;
  enriched_at: string | null;
}

export interface ToolItem {
  id: number;
  name: string;
  slug: string | null;
  description: string | null;
  url: string | null;
  website_url: string | null;
  pricing: string | null;
  category: string | null;
  source: string | null;
  status: string | null;
  features: string[] | null;
  target_audience: string | null;
  fetched_at: string | null;
  enriched_at: string | null;
}

export interface Stats {
  news_gesamt: number;
  tools_gesamt: number;
}

export async function fetchNews(params?: {
  source?: string;
  category?: string;
  limit?: number;
  offset?: number;
}): Promise<NewsItem[]> {
  const searchParams = new URLSearchParams();
  if (params?.source) searchParams.set('source', params.source);
  if (params?.category) searchParams.set('category', params.category);
  searchParams.set('limit', String(params?.limit || 20));
  searchParams.set('offset', String(params?.offset || 0));

  const res = await fetch(`${API_BASE}/api/news?${searchParams}`, {
    next: { revalidate: 120 },
  });
  if (!res.ok) throw new Error('Fehler beim Laden der News');
  return res.json();
}

export async function fetchNewsById(id: number): Promise<NewsItem> {
  const res = await fetch(`${API_BASE}/api/news/${id}`, {
    next: { revalidate: 120 },
  });
  if (!res.ok) throw new Error('News nicht gefunden');
  return res.json();
}

export async function fetchNewsSources(): Promise<string[]> {
  const res = await fetch(`${API_BASE}/api/news/sources`, {
    next: { revalidate: 300 },
  });
  if (!res.ok) return [];
  return res.json();
}

export async function fetchTools(params?: {
  source?: string;
  category?: string;
  pricing?: string;
  status?: string;
  limit?: number;
  offset?: number;
}): Promise<ToolItem[]> {
  const searchParams = new URLSearchParams();
  if (params?.source) searchParams.set('source', params.source);
  if (params?.category) searchParams.set('category', params.category);
  if (params?.pricing) searchParams.set('pricing', params.pricing);
  if (params?.status) searchParams.set('status', params.status);
  searchParams.set('limit', String(params?.limit || 20));
  searchParams.set('offset', String(params?.offset || 0));

  const res = await fetch(`${API_BASE}/api/tools?${searchParams}`, {
    next: { revalidate: 120 },
  });
  if (!res.ok) throw new Error('Fehler beim Laden der Tools');
  return res.json();
}

export async function fetchToolBySlug(slug: string): Promise<ToolItem | null> {
  const res = await fetch(`${API_BASE}/api/tools/by-slug/${encodeURIComponent(slug)}`, {
    next: { revalidate: 120 },
  });
  if (!res.ok) return null;
  return res.json();
}

export async function fetchToolById(id: number): Promise<ToolItem> {
  const res = await fetch(`${API_BASE}/api/tools/${id}`, {
    next: { revalidate: 120 },
  });
  if (!res.ok) throw new Error('Tool nicht gefunden');
  return res.json();
}

export async function fetchToolCategories(): Promise<string[]> {
  const res = await fetch(`${API_BASE}/api/tools/categories`, {
    next: { revalidate: 300 },
  });
  if (!res.ok) return [];
  return res.json();
}

export async function fetchStats(): Promise<Stats> {
  const res = await fetch(`${API_BASE}/api/stats`, {
    next: { revalidate: 60 },
  });
  if (!res.ok) return { news_gesamt: 0, tools_gesamt: 0 };
  return res.json();
}
