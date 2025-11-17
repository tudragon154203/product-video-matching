import { StartJobRequest } from "../../../lib/zod/job";

describe("StartJobRequest schema", () => {
  const validBase = {
    query: "ergonomic pillows",
    top_amz: 10,
    top_ebay: 5,
    platforms: ["youtube" as const],
    recency_days: 365,
  };

  it("accepts a valid request", () => {
    const result = StartJobRequest.safeParse(validBase);
    expect(result.success).toBe(true);
  });

  it("rejects empty string query", () => {
    const result = StartJobRequest.safeParse({
      ...validBase,
      query: "",
    });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues[0].message).toBe("Query must not be empty");
    }
  });

  it("rejects whitespace-only query (after trim)", () => {
    const result = StartJobRequest.safeParse({
      ...validBase,
      query: "   ",
    });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues[0].message).toBe("Query must not be empty");
    }
  });

  it("trims query when valid", () => {
    const result = StartJobRequest.safeParse({
      ...validBase,
      query: "  test query  ",
    });
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.query).toBe("test query");
    }
  });
});
