if os.getenv("MAKELOVE_CAPABILITY_SMOKE") == "1" then
    local file = io.open("version.txt", "w")
    if file ~= nil then
        file:write("__MAKELOVE_EXPECTED_VERSION__")
        file:close()
    end
    os.exit(0)
end

function love.draw()
    local major, minor, revision, codename = love.getVersion()
    love.graphics.print("Capability Project", 10, 32)
    love.graphics.print(string.format("Love version: %d.%d.%d - %s", major, minor, revision, codename), 10, 48)
end
