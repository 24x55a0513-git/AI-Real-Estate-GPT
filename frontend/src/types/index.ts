export type ListingType = "buy" | "rent";
export type PropertyType = "apartment" | "independent_house" | "villa" | "plot" | "commercial";
export type Furnishing = "furnished" | "semi_furnished" | "unfurnished";
export type PropertyStatus = "active" | "sold" | "rented" | "inactive";
export type Role = "user" | "admin";

export interface User { id: number; email: string; full_name: string; phone: string | null; role: Role; created_at: string }
export interface TokenResponse { access_token: string; token_type: string; expires_in: number; user: User }

export interface PropertyImage { id: number; url: string; alt: string | null }
export interface Property {
  id: number; title: string; description: string; city: string; locality: string; address: string | null;
  property_type: PropertyType; listing_type: ListingType; price: number; area_sqft: number; bedrooms: number;
  bathrooms: number; has_parking: boolean; furnishing: Furnishing | null; status: PropertyStatus; is_demo: boolean;
  amenities: string[]; images: PropertyImage[]; created_at: string;
}
export interface Page<T> { items: T[]; total: number; page: number; page_size: number; total_pages: number }
export interface Facets { cities: string[]; localities: Record<string, string[]>; amenities: string[]; property_types: PropertyType[] }

export interface PropertyInput {
  title: string; description: string; city: string; locality: string; address?: string | null;
  property_type: PropertyType; listing_type: ListingType; price: number; area_sqft: number; bedrooms: number;
  bathrooms: number; has_parking: boolean; furnishing: Furnishing | null; amenities: string[];
  status: PropertyStatus; is_demo: boolean; images: { url: string; alt?: string | null }[];
}

export interface SearchParams {
  city?: string; locality?: string; q?: string; listing_type?: ListingType; property_type?: PropertyType[];
  min_price?: number; max_price?: number; bedrooms?: number; bathrooms?: number; min_area?: number; max_area?: number;
  amenity?: string[]; has_parking?: boolean; furnishing?: Furnishing; status?: PropertyStatus;
  sort?: "newest" | "price_asc" | "price_desc"; page?: number; page_size?: number;
}

export interface CompareItem { property: Property; price_per_sqft: number | null }
export interface CompareResult {
  items: CompareItem[]; lowest_price_id: number | null; lowest_price_per_sqft_id: number | null;
  largest_area_id: number | null; differing_fields: string[]; notes: string[];
}

export interface Inquiry {
  id: number; property_id: number | null; property_title: string | null; name: string; email: string;
  phone: string | null; message: string; status: "new" | "contacted" | "closed"; created_at: string;
}
export interface InquiryInput { property_id?: number | null; name: string; email: string; phone?: string | null; message: string }

export interface SearchCriteria {
  city?: string | null; locality?: string | null; listing_type?: ListingType | null; property_types: PropertyType[];
  min_price?: number | null; max_price?: number | null; min_bedrooms?: number | null; max_bedrooms?: number | null;
  min_bathrooms?: number | null; min_area?: number | null; max_area?: number | null; has_parking?: boolean | null;
  furnishing?: Furnishing | null; amenities: string[]; sort?: "newest" | "price_asc" | "price_desc" | null;
}
export interface ChatSuggestion { label: string; criteria: SearchCriteria; match_count: number }
export interface ChatMatch { property: Property; reasons: string[] }
export interface ChatResponse {
  session_id: number | null; intent: string; reply: string; parser: string; criteria: SearchCriteria;
  matches: ChatMatch[]; total_matches: number; suggestions: ChatSuggestion[]; assumptions: string[];
  warnings: string[]; compare_ids: number[];
}
export interface ChatSession { id: number; title: string; updated_at: string }
export interface ChatSessionDetail extends ChatSession {
  messages: { id: number; role: "user" | "assistant"; content: string; created_at: string }[];
}
export interface AdminStats {
  total_properties: number; active_properties: number; sale_listings: number; rental_listings: number;
  inactive_properties: number; total_users: number; total_inquiries: number; new_inquiries: number;
  by_city: Record<string, number>; by_type: Record<string, number>;
}
export interface UserSummary { favorites: number; inquiries: number; chat_sessions: number }

export interface ChatSearchBody {
  message: string; session_id?: number | null; context_criteria?: SearchCriteria | null;
  criteria_override?: SearchCriteria | null;
}
