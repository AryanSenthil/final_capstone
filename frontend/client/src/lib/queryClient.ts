import { QueryClient, QueryFunction } from "@tanstack/react-query";

const defaultQueryFn: QueryFunction = async ({ queryKey }) => {
  // Build URL from queryKey parts
  // First element is the base path, subsequent elements are path segments or query strings
  let url = queryKey[0] as string;
  for (let i = 1; i < queryKey.length; i++) {
    const part = queryKey[i] as string;
    if (part.startsWith("?")) {
      // Query string - append directly
      url += part;
    } else {
      // Path segment - add with slash
      url += "/" + part;
    }
  }
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`API request failed: ${response.statusText}`);
  }
  return response.json();
};

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      queryFn: defaultQueryFn,
      staleTime: 1000 * 60 * 5, // 5 minutes
      refetchOnWindowFocus: false,
    },
  },
});

export async function apiRequest(
  method: string,
  url: string,
  body?: unknown
): Promise<Response> {
  const options: RequestInit = {
    method,
    headers: {
      "Content-Type": "application/json",
    },
  };

  if (body) {
    options.body = JSON.stringify(body);
  }

  const response = await fetch(url, options);

  if (!response.ok) {
    throw new Error(`API request failed: ${response.statusText}`);
  }

  return response;
}
