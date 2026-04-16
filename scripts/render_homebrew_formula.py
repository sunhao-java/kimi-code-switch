from __future__ import annotations

import argparse
from pathlib import Path


FORMULA_TEMPLATE = """class KimiCodeSwitch < Formula
  desc "Terminal UI for managing kimi-code-cli providers, models, and profiles"
  homepage "https://github.com/{github_repo}"
  version "{version}"

  on_macos do
    if Hardware::CPU.arm?
      url "https://github.com/{github_repo}/releases/download/v#{{version}}/kimi-code-switch-v#{{version}}-macos-arm64.tar.gz"
      sha256 "{arm64_sha256}"
    else
      url "https://github.com/{github_repo}/releases/download/v#{{version}}/kimi-code-switch-v#{{version}}-macos-amd64.tar.gz"
      sha256 "{amd64_sha256}"
    end
  end

  livecheck do
    url :stable
    regex(/^v?(\\d+\\.\\d+\\.\\d+)$/i)
  end

  def install
    bin.install "kimi-code-switch"
  end

  test do
    assert_match "Terminal UI for kimi-code-cli config.toml", shell_output("#{{bin}}/kimi-code-switch --help")
  end
end
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render Homebrew formula for kimi-code-switch release assets.",
    )
    parser.add_argument("--version", required=True, help="Release version without leading v")
    parser.add_argument("--github-repo", required=True, help="GitHub repo in owner/name form")
    parser.add_argument("--arm64-sha256", required=True, help="SHA256 for macOS arm64 asset")
    parser.add_argument("--amd64-sha256", required=True, help="SHA256 for macOS amd64 asset")
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output formula path",
    )
    return parser


def render_formula(version: str, github_repo: str, arm64_sha256: str, amd64_sha256: str) -> str:
    return FORMULA_TEMPLATE.format(
        version=version,
        github_repo=github_repo,
        arm64_sha256=arm64_sha256,
        amd64_sha256=amd64_sha256,
    )


def main() -> int:
    args = build_parser().parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        render_formula(
            version=args.version,
            github_repo=args.github_repo,
            arm64_sha256=args.arm64_sha256,
            amd64_sha256=args.amd64_sha256,
        ),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
