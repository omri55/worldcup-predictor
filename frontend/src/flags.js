// Country -> flag emoji. Renders as real flags on iOS/macOS (the target).
const FLAGS = {
  Algeria: "🇩🇿", Argentina: "🇦🇷", Australia: "🇦🇺", Austria: "🇦🇹",
  Belgium: "🇧🇪", "Bosnia and Herzegovina": "🇧🇦", Brazil: "🇧🇷", Canada: "🇨🇦",
  "Cape Verde": "🇨🇻", Chile: "🇨🇱", Colombia: "🇨🇴", Croatia: "🇭🇷",
  "Curaçao": "🇨🇼", "Czech Republic": "🇨🇿", "DR Congo": "🇨🇩", Denmark: "🇩🇰",
  Ecuador: "🇪🇨", Egypt: "🇪🇬", England: "🏴󠁧󠁢󠁥󠁮󠁧󠁿", France: "🇫🇷", Germany: "🇩🇪",
  Ghana: "🇬🇭", Greece: "🇬🇷", Haiti: "🇭🇹", Iran: "🇮🇷", Iraq: "🇮🇶", Italy: "🇮🇹",
  "Ivory Coast": "🇨🇮", Japan: "🇯🇵", Jersey: "🇯🇪", Jordan: "🇯🇴", Kosovo: "🇽🇰",
  Mexico: "🇲🇽", Morocco: "🇲🇦", Netherlands: "🇳🇱", "New Zealand": "🇳🇿",
  Nigeria: "🇳🇬", Norway: "🇳🇴", Panama: "🇵🇦", Paraguay: "🇵🇾", Poland: "🇵🇱",
  Portugal: "🇵🇹", Qatar: "🇶🇦", Russia: "🇷🇺", "Saudi Arabia": "🇸🇦",
  Scotland: "🏴󠁧󠁢󠁳󠁣󠁴󠁿", Senegal: "🇸🇳", Serbia: "🇷🇸", "South Africa": "🇿🇦",
  "South Korea": "🇰🇷", Spain: "🇪🇸", Sweden: "🇸🇪", Switzerland: "🇨🇭",
  Tunisia: "🇹🇳", Turkey: "🇹🇷", Ukraine: "🇺🇦", "United States": "🇺🇸",
  Uruguay: "🇺🇾", Uzbekistan: "🇺🇿", Venezuela: "🇻🇪",
  Wales: "🏴󠁧󠁢󠁷󠁬󠁳󠁿", Portugal: "🇵🇹",
};

export function flag(team) {
  return FLAGS[team] || "🏳️";
}
