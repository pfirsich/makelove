--[[
    Handler used to convert lua code to bytecode.
    This is setup as a 'game', so that the love binary that we are appending to can run this.
]]

function love.load()
    -- Read input from stdin
    -- This is base64 encoded to ensure no translation occurs on windows
    local source = love.data.decode("string", "base64", io.read())
    -- Load the data
    local lua_data = assert(load(source))
    -- Convert to bytecode, strip debug symbols
    local stripped = assert(string.dump(lua_data, true))
    -- Encode the bytecode to base64 again
    local encoded = love.data.encode('string', 'base64', stripped, 0)
    -- Send it back
    io.write(encoded)
    -- Great success
    os.exit(0, true)
end

function love.errorhandler(msg)
    msg = tostring(msg)
    print(msg)
    os.exit(1, true)
end
