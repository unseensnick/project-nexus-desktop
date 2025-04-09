import eslint from "@electron-toolkit/eslint-config"
import eslintConfigPrettier from "@electron-toolkit/eslint-config-prettier"
import eslintPluginPrettier from "eslint-plugin-prettier"
import eslintPluginReact from "eslint-plugin-react"
import eslintPluginReactHooks from "eslint-plugin-react-hooks"
import eslintPluginReactRefresh from "eslint-plugin-react-refresh"

export default [
	{ ignores: ["**/node_modules", "**/dist", "**/out"] },
	eslint,
	eslintPluginReact.configs.flat.recommended,
	eslintPluginReact.configs.flat["jsx-runtime"],
	{
		settings: {
			react: {
				version: "detect"
			}
		}
	},
	{
		files: ["**/*.{js,jsx}"],
		plugins: {
			"react-hooks": eslintPluginReactHooks,
			"react-refresh": eslintPluginReactRefresh,
			prettier: eslintPluginPrettier
		},
		rules: {
			...eslintPluginReactHooks.configs.recommended.rules,
			...eslintPluginReactRefresh.configs.vite.rules,

			"react/prop-types": "off",
			"react/no-unescaped-entities": "off",
			"no-unused-vars": "off",
			"react-refresh/only-export-components": "off",

			"prettier/prettier": "off"
		}
	},
	eslintConfigPrettier
]
