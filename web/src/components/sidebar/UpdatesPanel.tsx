import type { UpdateItem } from "../../lib/types";
import { formatAgo } from "../../lib/utils";

const isEmoji = (s: string) => !!s && /\p{Extended_Pictographic}/u.test(s);

// Same slug cleaner used above
const cleanTitle = (t?: string) => {
  if (!t) return t;
  return t
    .replace(/^(?:[a-z0-9]+-){1,3}(?=[A-Z])/i, "")
    .replace(/^(?:[a-z0-9]+-){1,3}\s+/i, "");
};

export default function UpdatesPanel({
  activeTab,
  setActiveTab,
  localUpdates,
  globalUpdates,
  loadingLocal,
  loadingGlobal,
  selectedLL,
  onView,
  reactionsById,
  onReact,
}: {
  activeTab: "local" | "global";
  setActiveTab: (t: "local" | "global") => void;
  localUpdates: UpdateItem[];
  globalUpdates: UpdateItem[];
  loadingLocal: boolean;
  loadingGlobal: boolean;
  selectedLL: [number, number] | null;
  onView: (u: UpdateItem) => void;
  reactionsById: Record<string, any>;
  onReact: (rid: string, action: "verify" | "clear") => void;
}) {
  const renderList = (
    list: UpdateItem[],
    loading: boolean,
    emptyMsg: string
  ) => (
    <>
      {loading && <div className="muted">Loading…</div>}
      {!loading && list.length === 0 && <div className="muted">{emptyMsg}</div>}
      {!loading &&
        list.map((u, i) => {
          // get reaction info
          const rid = u.rid;
          const rx = rid ? reactionsById[rid] : null;
          const meVerified = !!rx?.me?.verified;
          const meCleared = !!rx?.me?.cleared;
          const verifyCount = rx?.verify_count ?? 0;
          const clearCount = rx?.clear_count ?? 0;

          const showEmoji =
            u.emoji && isEmoji(String(u.emoji)) ? u.emoji : null;
          const title = cleanTitle(u.title) || u.title || "Update";

          return (
            <div className="updateItem" key={`${activeTab}-${i}`}>
              <div className="flex items-center gap-2">
                {showEmoji ? <div className="text-xl">{showEmoji}</div> : null}
                <div className="flex-1">
                  <div className="font-medium">{title}</div>
                  <div className="text-xs muted">
                    {formatAgo(u.time)} · {u.kind}
                    {u.severity ? <> · {String(u.severity)}</> : null}
                  </div>
                  {u.sourceUrl && (
                    <div className="text-xs">
                      <a
                        className="link"
                        href={u.sourceUrl}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Source
                      </a>
                    </div>
                  )}
                </div>
                {u.kind === "report" && rid ? (
                  <>
                    <button
                      className={`btn btn-ghost ${
                        meVerified ? "btn-active" : ""
                      }`}
                      onClick={() => onReact(rid, "verify")}
                      title="Others also saw/heard this"
                    >
                      {meVerified ? "Verified" : "Verify"} · {verifyCount}
                    </button>
                    <button
                      className={`btn btn-ghost ${
                        meCleared ? "btn-active" : ""
                      }`}
                      onClick={() => onReact(rid, "clear")}
                      title="Issue is cleared/resolved"
                    >
                      {meCleared ? "Cleared" : "Clear"} · {clearCount}
                    </button>
                  </>
                ) : null}
                <button className="btn btn-ghost" onClick={() => onView(u)}>
                  View
                </button>
              </div>
            </div>
          );
        })}
    </>
  );

  return (
    <div
      className="block"
      style={{ display: "flex", flexDirection: "column", gap: 8 }}
    >
      <div className="tabs" style={{ flex: "0 0 auto" }}>
        <button
          className={`tab ${activeTab === "local" ? "tab-active" : ""}`}
          onClick={() => setActiveTab("local")}
        >
          Local updates
        </button>
        <button
          className={`tab ${activeTab === "global" ? "tab-active" : ""}`}
          onClick={() => setActiveTab("global")}
        >
          Global updates
        </button>
      </div>
      <div
        className="updates"
        style={{
          flex: "0 0 auto",
          height: "50vh",
          overflowY: "auto",
          overflowX: "hidden",
          paddingRight: 4,
        }}
        onWheel={(e) => e.stopPropagation()}
      >
        {activeTab === "local" ? (
          selectedLL ? (
            renderList(localUpdates, loadingLocal, "No recent updates here.")
          ) : (
            <div className="muted">
              Pick a point (search/📍/click) to load local updates within 25
              miles (last 48h).
            </div>
          )
        ) : (
          renderList(
            globalUpdates,
            loadingGlobal,
            "No global updates right now."
          )
        )}
      </div>
    </div>
  );
}
